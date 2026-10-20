#include "runtime.h"

#include <stdio.h>
#include <string.h>

static size_t init_calls, term_calls;

/*
 * sceNetCtlInit
 *
 * NetCtl initialization itself does not need to establish an actual network
 * connection. Ratchet can continue into the NP/toolkit initialization path;
 * later NetCtl calls are implemented only when the game actually reaches them.
 */
static ABI int32_t netctl_init(void)
{
    ++init_calls;
    puts("Runtime: sceNetCtlInit -> OK");
    return 0;
}

static ABI int32_t netctl_term(void)
{
    ++term_calls;
    puts("Runtime: sceNetCtlTerm -> OK");
    return 0;
}

uintptr_t runtime_netctl_resolve(const char *name)
{
    if (!strcmp(name, "gky0+oaNM4k#libSceNetCtl"))
        return (uintptr_t)netctl_init;

    if (!strcmp(name, "Z4wwCFiBELQ#libSceNetCtl"))
        return (uintptr_t)netctl_term;

    return 0;
}

void runtime_netctl_report(void)
{
    printf(
        "Runtime: NetCtl init calls=%zu, term calls=%zu\n",
        init_calls,
        term_calls
    );
}
