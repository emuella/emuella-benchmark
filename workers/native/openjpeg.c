/* Adapter over the installed OpenJPEG public API; no codec implementation. */
#include <limits.h>
#include <openjpeg.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>

typedef struct {
  unsigned char *data;
  size_t len, capacity, pos;
  int owned;
} memory;
static OPJ_SIZE_T read_memory(void *out, OPJ_SIZE_T n, void *ctx) {
  memory *m = ctx;
  if (m->pos >= m->len)
    return (OPJ_SIZE_T)-1;
  if (n > m->len - m->pos)
    n = m->len - m->pos;
  memcpy(out, m->data + m->pos, n);
  m->pos += n;
  return n;
}
static int reserve(memory *m, size_t size) {
  if (size <= m->capacity)
    return 1;
  size_t cap = size > m->capacity * 2 ? size : m->capacity * 2;
  void *p = realloc(m->data, cap);
  if (!p)
    return 0;
  m->data = p;
  m->capacity = cap;
  return 1;
}
static OPJ_SIZE_T write_memory(void *in, OPJ_SIZE_T n, void *ctx) {
  memory *m = ctx;
  if (n > SIZE_MAX - m->pos || !reserve(m, m->pos + n))
    return (OPJ_SIZE_T)-1;
  memcpy(m->data + m->pos, in, n);
  m->pos += n;
  if (m->pos > m->len)
    m->len = m->pos;
  return n;
}
static OPJ_BOOL seek_memory(OPJ_OFF_T pos, void *ctx) {
  memory *m = ctx;
  if (pos < 0 || (uint64_t)pos > SIZE_MAX)
    return OPJ_FALSE;
  if (m->owned && (size_t)pos > m->len) {
    if (!reserve(m, (size_t)pos))
      return OPJ_FALSE;
    memset(m->data + m->len, 0, (size_t)pos - m->len);
    m->len = (size_t)pos;
  }
  if ((size_t)pos > m->len)
    return OPJ_FALSE;
  m->pos = (size_t)pos;
  return OPJ_TRUE;
}
static OPJ_OFF_T skip_memory(OPJ_OFF_T n, void *ctx) {
  memory *m = ctx;
  if (m->pos > INT64_MAX || (n > 0 && n > INT64_MAX - (int64_t)m->pos))
    return -1;
  return seek_memory((OPJ_OFF_T)m->pos + n, ctx) ? n : -1;
}
static opj_stream_t *stream(memory *m, int reading) {
  opj_stream_t *s = opj_stream_create(65536, reading);
  if (!s)
    return NULL;
  opj_stream_set_user_data(s, m, NULL);
  opj_stream_set_user_data_length(s, m->len);
  if (reading)
    opj_stream_set_read_function(s, read_memory);
  else
    opj_stream_set_write_function(s, write_memory);
  opj_stream_set_skip_function(s, skip_memory);
  opj_stream_set_seek_function(s, seek_memory);
  return s;
}
void benchmark_openjpeg_free(void *p) { free(p); }
int benchmark_openjpeg_encode(const int32_t *samples, uint32_t w, uint32_t h,
                              uint32_t components, uint32_t bits, int levels,
                              int lossless, double ratio, int threads,
                              unsigned char **out, size_t *len) {
  int ok = 0;
  memory m = {0};
  m.owned = 1;
  opj_stream_t *s = NULL;
  opj_codec_t *codec = NULL;
  opj_image_t *image = NULL;
  opj_image_cmptparm_t params[3];
  memset(params, 0, sizeof(params));
  if (components != 1 && components != 3)
    return 0;
  for (uint32_t c = 0; c < components; c++) {
    params[c].dx = 1;
    params[c].dy = 1;
    params[c].w = w;
    params[c].h = h;
    params[c].prec = bits;
  }
  image = opj_image_create(components, params,
                           components == 1 ? OPJ_CLRSPC_GRAY : OPJ_CLRSPC_SRGB);
  if (!image)
    goto done;
  image->x1 = w;
  image->y1 = h;
  for (size_t p = 0; p < (size_t)w * h; p++)
    for (uint32_t c = 0; c < components; c++)
      image->comps[c].data[p] = samples[p * components + c];
  opj_cparameters_t options;
  opj_set_default_encoder_parameters(&options);
  options.numresolution = levels + 1;
  options.tcp_numlayers = 1;
  options.cp_disto_alloc = 1;
  options.tcp_rates[0] = lossless ? 0 : (float)ratio;
  options.irreversible = !lossless;
  options.tcp_mct = 0;
  options.prog_order = OPJ_LRCP;
  codec = opj_create_compress(OPJ_CODEC_J2K);
  if (!codec || !opj_setup_encoder(codec, &options, image) ||
      !opj_codec_set_threads(codec, threads))
    goto done;
  s = stream(&m, 0);
  if (!s || !opj_start_compress(codec, image, s) || !opj_encode(codec, s) ||
      !opj_end_compress(codec, s))
    goto done;
  *out = m.data;
  *len = m.len;
  m.data = NULL;
  ok = 1;
done:
  if (s)
    opj_stream_destroy(s);
  if (codec)
    opj_destroy_codec(codec);
  if (image)
    opj_image_destroy(image);
  free(m.data);
  return ok;
}
int benchmark_openjpeg_decode(const unsigned char *input, size_t len,
                              uint32_t source_w, uint32_t source_h, uint32_t w,
                              uint32_t h, uint32_t components, uint32_t bits,
                              int reduction, int roi, uint32_t x0, uint32_t y0,
                              uint32_t x1, uint32_t y1, int threads,
                              int32_t **out) {
  int ok = 0;
  memory m = {(unsigned char *)input, len, len, 0, 0};
  opj_stream_t *s = NULL;
  opj_codec_t *codec = NULL;
  opj_image_t *image = NULL;
  int32_t *pixels = NULL;
  opj_dparameters_t options;
  opj_set_default_decoder_parameters(&options);
  options.cp_reduce = reduction;
  codec = opj_create_decompress(OPJ_CODEC_J2K);
  if (!codec || !opj_setup_decoder(codec, &options) ||
      !opj_codec_set_threads(codec, threads))
    goto done;
  s = stream(&m, 1);
  if (!s || !opj_read_header(s, codec, &image))
    goto done;
  if (image->x0 || image->y0 || image->x1 != source_w || image->y1 != source_h)
    goto done;
  if (roi && !opj_set_decode_area(codec, image, (OPJ_INT32)x0, (OPJ_INT32)y0,
                                  (OPJ_INT32)x1, (OPJ_INT32)y1))
    goto done;
  if (!opj_decode(codec, s, image) || !opj_end_decompress(codec, s) ||
      image->numcomps != components)
    goto done;
  for (uint32_t c = 0; c < components; c++)
    if (image->comps[c].w != w || image->comps[c].h != h ||
        image->comps[c].prec != bits || image->comps[c].sgnd ||
        image->comps[c].dx != 1 || image->comps[c].dy != 1)
      goto done;
  if ((size_t)w > SIZE_MAX / h / components / sizeof(int32_t))
    goto done;
  pixels = malloc((size_t)w * h * components * sizeof(int32_t));
  if (!pixels)
    goto done;
  for (size_t p = 0; p < (size_t)w * h; p++)
    for (uint32_t c = 0; c < components; c++)
      pixels[p * components + c] = image->comps[c].data[p];
  *out = pixels;
  pixels = NULL;
  ok = 1;
done:
  free(pixels);
  if (s)
    opj_stream_destroy(s);
  if (codec)
    opj_destroy_codec(codec);
  if (image)
    opj_image_destroy(image);
  return ok;
}
