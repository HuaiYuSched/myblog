---
layout: single
title: "Build a new Hypercall system by imitating the syscall"
modified:
categories: 
excerpt:
tags: []
image:
  feature:
  teaser: home.jpg
  thumb:
---

Build the new Hypercall system by imitating the syscall.

####The work-flow of native syscall.
I know most of you know how it works, and I also introduced before, but I'd like to give a brief introduction about the syscall again to help you know how the hypercall builds.

1. The syscall register in interrupt system, the invocation of function is lactate in pok_event_init().

2. The syscall is invoked by program, but not by hardware, when we using the pok_syscallx which is a macro of pok_do_syscall. Finally, the pok_do_syscall will invoke the "int 42".

3. When the syscall is invoked, the register handler, syscall_gate will be invoked, the syscall_gate is defined in kernel/arch/x86/syscall.c and kernel/include/arch/x86/interrupt.h 

4. The syscall_gate will invoked the pok_core_syscall, which will tackle the syscall according to the syscall_id which is defined in two places: kernel/include/core/syscall.h and libpok/include/core/syscall.h

I have draw a illustrated to describe it.

![The workflow of syscall]({{site.img_url}}/The\ workflow\ of\ syscall.jpg)


#### The imitation of hypercall.

As I described beyond and can be seen in the github, What we should do is just a copy and paste job, 

1. Add a pok_hypercall_init in pok_event_init, also should add POK_NEES_X86_VMM to guard this function.

2. Add the two head file, kernel/include/core/hypercall.h and libpok/include/core/hypercall.h, and build the corresponding structure and declaration.

3. implement the corresponding functions in corresponding .c files. That is:

  a. kernel/arch/x86/hypercall.c, using this file to build the hypercall_gate.

  b. kernel/core/hypercall.c, in this file, the pok_core_hypercall will deal with the hypercall.

  c. modify the kernel/include/arch/x86/interrupt.h, add the support of hypercall handler.

  d. add libpok/arch/x86/hypercall.c, in this file, we implement the pok_do_hypercall, which will invoke the soft interrupt.

4. modified interrelated Makefile to assure those file will work when the BSP is x86-qemu-vmm, also will not influence the normal POK, when the BSP is not x86-qemu-vmm.

####Test

Add a new example named testHypercall. This example is derived from myHelloword, and the BSP is modified as x86-qemu-vmm in file model.addl. Also all the syscall in hello.c has been replaced with hypercall.

Here is the result:

![The result of hypercall]({{site.img_url)}}/The\ result\ of\ hypercall.jpg)

As we can see, the hypercall is working and get the time tick from POK.
