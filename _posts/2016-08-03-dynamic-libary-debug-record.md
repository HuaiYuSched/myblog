---
layout: single
title: "Dynamic Library Debug Record"
modified:
categories:
excerpt:
tags: []
image:
  feature:
  teaser:
  thumb:
date: 2016-08-03T01:43:40+08:00
---

Recently, I have encountered a bug due to an upgrade of the OpenSSL library on Ubuntu 16.04.   
The bug is quite tricky because it's related to how Linux load a dynamic library. So here I write This note to record it.

## background
I'm working on Nginx on OFP when I encounter this bug. Previously I found that Nginx on OFP may loss the link connection if the network throughput is heavy. So I trying to rebuild the Nginx on OFP with debug information. However, When I running the rebuild Nginx, below message shows.   

```
[1]    8597 segmentation fault (core dumped)  ./objs/nginx
```

# Symptom
**A segmentation fault!**   
It's impossible because I did not change any code since last successful compilation.
What's more, seems it crashed before the main function...    
# Debugging by GDB
Using GDB, The crash stack list below:   

```
#0  0x0000000000000000 in ?? ()
#1  0x0000000000437ec1 in close (fd=<optimized out>) at src/event/modules/ngx_ofp_module.c:495
#2  0x00007ffff73d8ead in RAND_poll () from /lib/x86_64-linux-gnu/libcrypto.so.1.0.0
#3  0x00007ffff73d7bd5 in ?? () from /lib/x86_64-linux-gnu/libcrypto.so.1.0.0
#4  0x00007ffff73d8603 in ?? () from /lib/x86_64-linux-gnu/libcrypto.so.1.0.0
#5  0x00007ffff744e288 in ?? () from /lib/x86_64-linux-gnu/libcrypto.so.1.0.0
#6  0x00007ffff744e914 in ?? () from /lib/x86_64-linux-gnu/libcrypto.so.1.0.0
#7  0x00007ffff73d8993 in RAND_init_fips () from /lib/x86_64-linux-gnu/libcrypto.so.1.0.0
#8  0x00007ffff731bf7a in OPENSSL_init_library () from /lib/x86_64-linux-gnu/libcrypto.so.1.0.0
#9  0x00007ffff7de74ea in call_init (l=<optimized out>, argc=argc@entry=1,
    argv=argv@entry=0x7fffffffe7e8, env=env@entry=0x7fffffffe7f8) at dl-init.c:72
#10 0x00007ffff7de75fb in call_init (env=0x7fffffffe7f8, argv=0x7fffffffe7e8, argc=1, l=<optimized out>)
    at dl-init.c:30
#11 _dl_init (main_map=0x7ffff7ffe168, argc=1, argv=0x7fffffffe7e8, env=0x7fffffffe7f8) at dl-init.c:120
#12 0x00007ffff7dd7cfa in _dl_start_user () from /lib64/ld-linux-x86-64.so.2
#13 0x0000000000000001 in ?? ()
#14 0x00007fffffffeaa8 in ?? ()
#15 0x0000000000000000 in ?? ()
```

Surprisingly, Why the libcrypto invoked a function in Nginx OFP modules? Of course it should crash because the Nginx haven't initialized.   
Here is the close function in nginx_ofp.   

```c
int close(int fd)
{
  if (fd & (1 << ODP_FD_BITS)) {
    fd &= ~(1 << ODP_FD_BITS);
    return ofp_close(fd);
  } else {
    return real_close(fd);
  }
}
```

As we can see, it will invoke ofp_close when this fd(file descriptor) is odp-type, or invoke the real_close function.   
Step in GDB, the real_close is NULL, that's the reason of segmentation fault.   

Here is the definition of real_close:   

```c
static int (*real_close)(int);
```

Because the static integer without initialization in C language is stored in the .bss section in ELF file and is all-zero, the real_close is zero in this case.

# Reason
Now we clearly know this problem occurs because the libcrypto should not invoke close in Nginx OFP module, but why it does is still obscure.   

## LD_DEBUG
To get an insight of dynamic library load in Linux, especially when the program do not works, we can use LD_DEBUG.  

```
 LD_DEBUG = all ./objs/nginx
8939:     symbol=close;  lookup in file=objs/nginx [0]
8939:     binding file /lib/x86_64-linux-gnu/libcrypto.so.1.0.0 [0] to objs/nginx [0]: normal symbol `close' [GLIBC_2.2.5]
8939:     symbol=close;  lookup in file=objs/nginx [0]
8939:     binding file /lib/x86_64-linux-gnu/libcrypto.so.1.0.0 [0] to objs/nginx [0]: normal symbol `close' [GLIBC_2.2.5]
```

The newest version openssl library will invoke close function. However, due to PLT mechanism, the real address of close function can't be determine on compilation. As a result, the libcrypto will seeking close symbol in ELF files and other libraries. That's the reason why the libcrypto will invoke the close function in Nginx: the Nginx redefined close.    
The previous version OpenSSL do not invoke close function during library initialization.   
Furthermore, why it won't crash after ngx_ofp_init? Because ngx_ofp_init find the real address of close function in Glibc and assign it to real_close.   

```c
#define INIT_FUNCTION(func) \
        real_##func = dlsym(RTLD_NEXT, #func); \
        assert(real_##func)
  INIT_FUNCTION(close);
#undef INIT_FUNCTION
```

# Fix
Understanding all the details about this bug, how to fix it is so obvious. Just determine the value of real_close, if it's zero, assign it with the address of the close in Glibc.

```c
int close(int fd)
{
  if (fd & (1 << ODP_FD_BITS)) {
    fd &= ~(1 << ODP_FD_BITS);
    return OFP_close(fd);
  } else {
#define UNLIKELY(x) __builtin_expect(!!(x), 0)
    if(UNLIKELY(real_close == NULL))
      real_close = dlsym(RTLD_NEXT,"close");
#undef UNLIKELY
    return real_close(fd);
  }
}
```

