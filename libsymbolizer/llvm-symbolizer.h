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

typedef struct llvm_symbol_s {
    char *name;
    char *filename;
    int lineno;
    int column;
    char *error;
} llvm_symbol_t;

void llvm_symbolizer_lib_init(void);
void llvm_symbolizer_lib_cleanup(void);

llvm_symbolizer_t *llvm_symbolizer_new(void);
void llvm_symbolizer_free(llvm_symbolizer_t *sym);
llvm_symbol_t *llvm_symbolizer_symbolize(
    llvm_symbolizer_t *sym,
    const char *module,
    unsigned long long offset,
    int is_data);

void llvm_symbol_free(llvm_symbol_t *sym);

#ifdef __cplusplus
}
#endif

#endif
