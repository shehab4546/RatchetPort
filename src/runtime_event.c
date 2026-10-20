/* Ratchet & Clank CUSA01047 kernel EventFlag runtime. */
#define _GNU_SOURCE
#include "runtime.h"

#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <pthread.h>
#include <errno.h>
#include <time.h>

#define ERR(n) ((int32_t)(UINT32_C(0x80020000) | (n)))

typedef struct RatchetEventFlag {
    pthread_mutex_t mutex;
    pthread_cond_t changed;
    pthread_cond_t drained;

    uint64_t bits;

    uint32_t attr;
    unsigned waiters;

    int deleted;
} RatchetEventFlag;

static size_t event_created;
static size_t event_deleted;
static size_t event_waits;
static size_t event_sets;
static size_t event_timeouts;

static int valid_attr(uint32_t attr)
{
    uint32_t queue = attr & 0x0f;
    uint32_t threads = attr & 0xf0;

    if (attr & ~0x33u)
        return 0;

    if (queue != 0 && queue != 1 && queue != 2)
        return 0;

    if (threads != 0 &&
        threads != 0x10 &&
        threads != 0x20)
        return 0;

    return 1;
}

static int valid_wait_mode(uint32_t mode)
{
    uint32_t wait = mode & 0x0f;
    uint32_t clear = mode & 0xf0;

    if (mode & ~0x33u)
        return 0;

    if (wait != 1 && wait != 2)
        return 0;

    if (clear != 0 &&
        clear != 0x10 &&
        clear != 0x20)
        return 0;

    return 1;
}

static int condition_met(
    const RatchetEventFlag *event,
    uint64_t pattern,
    uint32_t mode)
{
    if ((mode & 0x0f) == 1)
        return (event->bits & pattern) == pattern;

    return (event->bits & pattern) != 0;
}

static void apply_clear(
    RatchetEventFlag *event,
    uint64_t pattern,
    uint32_t mode)
{
    switch (mode & 0xf0) {
    case 0:
        break;

    case 0x10:
        event->bits = 0;
        break;

    case 0x20:
        event->bits &= ~pattern;
        break;
    }
}

static ABI int32_t event_create(
    RatchetEventFlag **out,
    const char *name,
    uint32_t attr,
    uint64_t initial,
    const void *options)
{
    if (!out || !name || options || !valid_attr(attr))
        return ERR(22);

    if (strlen(name) >= 32)
        return ERR(63); /* ENAMETOOLONG */

    RatchetEventFlag *event =
        calloc(1, sizeof(*event));

    if (!event)
        return ERR(12);

    int e = pthread_mutex_init(&event->mutex, NULL);
    if (e) {
        free(event);
        return ERR(12);
    }

    e = pthread_cond_init(&event->changed, NULL);
    if (e) {
        pthread_mutex_destroy(&event->mutex);
        free(event);
        return ERR(12);
    }

    e = pthread_cond_init(&event->drained, NULL);
    if (e) {
        pthread_cond_destroy(&event->changed);
        pthread_mutex_destroy(&event->mutex);
        free(event);
        return ERR(12);
    }

    event->attr = attr;
    event->bits = initial;

    *out = event;
    ++event_created;

    return 0;
}

static ABI int32_t event_delete(
    RatchetEventFlag *event)
{
    if (!event)
        return ERR(3);

    pthread_mutex_lock(&event->mutex);

    event->deleted = 1;

    pthread_cond_broadcast(&event->changed);

    while (event->waiters)
        pthread_cond_wait(
            &event->drained,
            &event->mutex);

    pthread_mutex_unlock(&event->mutex);

    pthread_cond_destroy(&event->drained);
    pthread_cond_destroy(&event->changed);
    pthread_mutex_destroy(&event->mutex);

    free(event);
    ++event_deleted;

    return 0;
}

static ABI int32_t event_set(
    RatchetEventFlag *event,
    uint64_t pattern)
{
    if (!event)
        return ERR(3);

    pthread_mutex_lock(&event->mutex);

    if (event->deleted) {
        pthread_mutex_unlock(&event->mutex);
        return ERR(13);
    }

    event->bits |= pattern;
    ++event_sets;

    /*
     * Wake all contenders. Each waiter re-tests AND/OR while
     * holding this mutex, so clear modes remain serialized.
     */
    pthread_cond_broadcast(&event->changed);

    pthread_mutex_unlock(&event->mutex);
    return 0;
}

static ABI int32_t event_wait(
    RatchetEventFlag *event,
    uint64_t pattern,
    uint32_t mode,
    uint64_t *result_pattern,
    uint32_t *timeout)
{
    if (!event)
        return ERR(3);

    if (!pattern || !valid_wait_mode(mode))
        return ERR(22);

    pthread_mutex_lock(&event->mutex);

    if (event->deleted) {
        pthread_mutex_unlock(&event->mutex);
        return ERR(13);
    }

    /*
     * 0x20 = multi waiter.
     * 0 / 0x10 = single waiter.
     */
    if ((event->attr & 0xf0) != 0x20 &&
        event->waiters) {
        pthread_mutex_unlock(&event->mutex);
        return ERR(1);
    }

    if (condition_met(event, pattern, mode)) {
        if (result_pattern)
            *result_pattern = event->bits;

        apply_clear(event, pattern, mode);

        pthread_mutex_unlock(&event->mutex);
        return 0;
    }

    if (timeout && *timeout == 0) {
        if (result_pattern)
            *result_pattern = event->bits;

        pthread_mutex_unlock(&event->mutex);

        ++event_timeouts;
        return ERR(60);
    }

    struct timespec deadline = {0};

    if (timeout) {
        struct timespec now;
        clock_gettime(CLOCK_REALTIME, &now);

        uint64_t ns =
            (uint64_t)now.tv_nsec +
            (uint64_t)(*timeout % 1000000u) * 1000u;

        deadline.tv_sec =
            now.tv_sec +
            (time_t)(*timeout / 1000000u) +
            (time_t)(ns / 1000000000u);

        deadline.tv_nsec =
            (long)(ns % 1000000000u);
    }

    ++event->waiters;
    ++event_waits;

    int32_t result = 0;

    for (;;) {
        int e;

        if (timeout) {
            e = pthread_cond_timedwait(
                &event->changed,
                &event->mutex,
                &deadline);
        } else {
            e = pthread_cond_wait(
                &event->changed,
                &event->mutex);
        }

        if (event->deleted) {
            result = ERR(13);
            break;
        }

        if (condition_met(event, pattern, mode)) {
            if (result_pattern)
                *result_pattern = event->bits;

            apply_clear(event, pattern, mode);
            result = 0;
            break;
        }

        if (e == ETIMEDOUT) {
            if (result_pattern)
                *result_pattern = event->bits;

            if (timeout)
                *timeout = 0;

            ++event_timeouts;
            result = ERR(60);
            break;
        }

        if (e) {
            result = ERR(22);
            break;
        }
    }

    --event->waiters;

    if (event->deleted && !event->waiters)
        pthread_cond_signal(&event->drained);

    pthread_mutex_unlock(&event->mutex);

    return result;
}

uintptr_t runtime_event_resolve(const char *name)
{
    if (!strcmp(
            name,
            "BpFoboUJoZU#libkernel"))
        return (uintptr_t)event_create;

    if (!strcmp(
            name,
            "JTvBflhYazQ#libkernel"))
        return (uintptr_t)event_wait;

    if (!strcmp(
            name,
            "8mql9OcQnd4#libkernel"))
        return (uintptr_t)event_delete;

    if (!strcmp(
            name,
            "IOnSvHzqu6A#libkernel"))
        return (uintptr_t)event_set;

    return 0;
}

void runtime_event_report(void)
{
    printf(
        "Runtime: event flags created=%zu, deleted=%zu, "
        "waits=%zu, sets=%zu, timeouts=%zu\n",
        event_created,
        event_deleted,
        event_waits,
        event_sets,
        event_timeouts);
}
