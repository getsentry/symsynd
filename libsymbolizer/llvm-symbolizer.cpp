//===-- llvm-symbolizer.cpp - Simple addr2line-like symbolizer ------------===//
//
//                     The LLVM Compiler Infrastructure
//
// This file is distributed under the University of Illinois Open Source
// License. See LICENSE.TXT for details.
//
//===----------------------------------------------------------------------===//
//
// This utility works much like "addr2line". It is able of transforming
// tuples (module name, module offset) to code locations (function name,
// file, line number, column number). It is targeted for compiler-rt tools
// (especially AddressSanitizer and ThreadSanitizer) that can use it
// to symbolize stack traces in their error reports.
//
//===----------------------------------------------------------------------===//

#include "llvm/ADT/StringRef.h"
#include "llvm/DebugInfo/Symbolize/DIPrinter.h"
#include "llvm/DebugInfo/Symbolize/Symbolize.h"
#include "llvm/Support/COM.h"
#include "llvm/Support/CommandLine.h"
#include "llvm/Support/Debug.h"
#include "llvm/Support/FileSystem.h"
#include "llvm/Support/ManagedStatic.h"
#include "llvm/Support/Path.h"
#include "llvm/Support/PrettyStackTrace.h"
#include "llvm/Support/Signals.h"
#include "llvm/Support/Error.h"
#include "llvm/Support/raw_ostream.h"
#include <cstdio>
#include <cstring>
#include <string>

#include "llvm-symbolizer.h"

using namespace llvm;
using namespace symbolize;

template<typename T>
static bool sym_failed(Expected<T> &expt, llvm_symbol_t *sym) {
    if (expt) {
        return false;
    }
    auto msg = toString(expt.takeError());
    free(sym->error);
    sym->error = strdup(msg.c_str());
    return true;
}

static int lib_initialized;
struct lib_shared_state {
    llvm_shutdown_obj *shutdown_obj;
};
struct llvm_symbolizer_s {
    LLVMSymbolizer *symbolizer;
};
static struct lib_shared_state *shared_state;

void
llvm_symbolizer_lib_init(void)
{
    if (lib_initialized) {
        return;
    }
    lib_initialized = 1;

    shared_state = (struct lib_shared_state *)malloc(sizeof(struct lib_shared_state));
    shared_state->shutdown_obj = new llvm_shutdown_obj();
}

void
llvm_symbolizer_lib_cleanup(void)
{
    if (!lib_initialized) {
        return;
    }
    lib_initialized = 0;

    delete shared_state->shutdown_obj;
    free(shared_state);
}

llvm_symbolizer_t *
llvm_symbolizer_new(void)
{
    if (!lib_initialized) {
        return 0;
    }
    llvm_symbolizer_t *rv = (llvm_symbolizer_t *)malloc(sizeof(llvm_symbolizer_t));

    LLVMSymbolizer::Options opts(
        FunctionNameKind::LinkageName, /* print functions */
        true, /* use symbol table */
        true, /* demangle */
        false, /* use relative address */
        "" /* default arch */
    );

    rv->symbolizer = new LLVMSymbolizer(opts);

    return rv;
}

void
llvm_symbolizer_free(llvm_symbolizer_t *sym)
{
    if (!sym) {
        return;
    }
    delete sym->symbolizer;
    free(sym);
}

llvm_symbol_t *
llvm_symbolizer_symbolize(
    llvm_symbolizer_t *self,
    const char *module,
    unsigned long long offset,
    int is_data)
{
    llvm_symbol_t *rv = (llvm_symbol_t *)malloc(sizeof(llvm_symbol_t));
    memset(rv, 0, sizeof(llvm_symbol_t));

    if (is_data) {
        auto res_or_err = self->symbolizer->symbolizeData(module, offset);
        if (sym_failed(res_or_err, rv)) {
            return rv;
        }
        auto res = res_or_err.get();
        rv->name = strdup(res.Name.c_str());
    } else {
        auto res_or_err = self->symbolizer->symbolizeCode(module, offset);
        if (sym_failed(res_or_err, rv)) {
            return rv;
        }
        auto res = res_or_err.get();
        rv->name = strdup(res.FunctionName.c_str());
        rv->filename = strdup(res.FileName.c_str());
        rv->lineno = res.Line;
        rv->column = res.Column;
    }

    return rv;
}

llvm_symbol_t *
llvm_symbolizer_symbolize_inlined(
    llvm_symbolizer_t *self,
    const char *module,
    unsigned long long offset,
    llvm_symbol_t ***sym_out,
    size_t *sym_count_out)
{
    // try to symbolicate or fail
    llvm_symbol_t *tmp = (llvm_symbol_t *)malloc(sizeof(llvm_symbol_t));
    memset(tmp, 0, sizeof(llvm_symbol_t));
    auto res_or_err = self->symbolizer->symbolizeInlinedCode(module, offset);
    if (sym_failed(res_or_err, tmp)) {
        return tmp;
    }

    auto res = res_or_err.get();
    size_t symCount = (size_t)res.getNumberOfFrames();

    llvm_symbol_t **syms = (llvm_symbol_t **)malloc(
        sizeof(llvm_symbolizer_t *) * symCount);

    for (size_t i = 0; i < symCount; i++) {
        auto symRes = res.getFrame(i);
        llvm_symbol_t *sym = tmp;
        if (!sym) {
            sym = (llvm_symbol_t *)malloc(sizeof(llvm_symbol_t));
            memset(sym, 0, sizeof(llvm_symbol_t));
        } else {
            tmp = 0;
        }
        sym->name = strdup(symRes.FunctionName.c_str());
        sym->filename = strdup(symRes.FileName.c_str());
        sym->lineno = symRes.Line;
        sym->column = symRes.Column;
        syms[i] = sym;
    }

    *sym_out = syms;
    *sym_count_out = symCount;
    return 0;
}

void
llvm_symbol_free(llvm_symbol_t *sym)
{
    if (!sym) {
        return;
    }
    free(sym->name);
    free(sym->filename);
    free(sym->error);
    free(sym);
}

void
llvm_bulk_symbol_free(llvm_symbol_t **syms, size_t count)
{
    if (!syms) {
        return;
    }

    for (size_t i = 0; i < count; i++) {
        llvm_symbol_free(syms[i]);
    }

    free(syms);
}
