#ifndef LIBDEBUG_H_INCLUDED
#define LIBDEBUG_H_INCLUDED

typedef void debug_info_t;

typedef struct {
    const char *message;
    int failed;
    int code;
} debug_error_t;

typedef struct {
    size_t len;
    const char *s;
} debug_str_slice_t;

typedef struct {
    debug_str_slice_t cpu_name;
    const char uuid[16];
    debug_str_slice_t name;
    uint64_t vmaddr;
    uint64_t vmsize;
} debug_variant_t;

debug_info_t *debug_info_open_path(
    const char *path, debug_error_t *err_out);
void debug_info_free(debug_info_t *di);
const char *debug_info_get_compilation_dir(
    debug_info_t *di, const char *cpu_name, const char *filename,
    debug_error_t *err_out);
debug_variant_t *debug_info_get_variants(
    const debug_info_t *di, int *variants_count, debug_error_t *err_out);
void debug_free_variants(debug_variant_t *variants);
void debug_buffer_free(void *buf);
debug_str_slice_t debug_get_cpu_name(int cputype, int cpusubtype,
    debug_error_t *err_out);

#endif
