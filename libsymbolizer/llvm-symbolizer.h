/**
 * This library exposes some of the functionality of llvm-symbolizer
 * as a simple dylib to be used from other programming languages.
 */

#ifndef LLVM_SYMBOLIZER_H_INCLUDED
#define LLVM_SYMBOLIZER_H_INCLUDED

#ifdef __cplusplus
extern "C" {
#endif

typedef unsigned long long llvm_addr_t;
struct llvm_symbolizer_s;
typedef struct llvm_symbolizer_s llvm_symbolizer_t;

typedef void (*llvm_symbolize_cb)(const char *, const char *, int, int);
typedef void (*llvm_symbolize_err_cb)(const char *);

void llvm_symbolizer_lib_init(void);
void llvm_symbolizer_lib_cleanup(void);

llvm_symbolizer_t *llvm_symbolizer_new(void);
void llvm_symbolizer_free(llvm_symbolizer_t *sym);
int llvm_symbolizer_symbolize(
    llvm_symbolizer_t *sym,
    llvm_symbolize_cb cb,
    llvm_symbolize_err_cb err_cb,
    const char *module,
    unsigned long long offset,
    int is_data);

#ifdef __cplusplus
}
#endif

#endif
