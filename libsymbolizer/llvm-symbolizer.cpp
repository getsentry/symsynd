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
#include "llvm/Support/raw_ostream.h"
#include <cstdio>
#include <cstring>
#include <string>

#include "llvm-symbolizer.h"

using namespace llvm;
using namespace symbolize;

template<typename T>
static bool failed(Expected<T> &expt, llvm_symbolize_err_cb cb) {
  if (expt) {
    return false;
  }
  auto msg = toString(expt.takeError());
  cb(msg.c_str());
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

int
llvm_symbolizer_symbolize(
    llvm_symbolizer_t *self,
    llvm_symbolize_cb cb,
    llvm_symbolize_err_cb err_cb,
    const char *module,
    unsigned long long offset,
    int is_data)
{
    if (is_data) {
        auto res_or_err = self->symbolizer->symbolizeData(module, offset);
        if (failed(res_or_err, err_cb)) {
            return 0;
        }
        auto res = res_or_err.get();
        cb(res.Name.c_str(), 0, 0, 0);
    } else {
        auto res_or_err = self->symbolizer->symbolizeCode(module, offset);
        if (failed(res_or_err, err_cb)) {
            return 0;
        }
        auto res = res_or_err.get();
        cb(res.FunctionName.c_str(), res.FileName.c_str(), res.Line, res.Column);
    }

    return 1;
}
