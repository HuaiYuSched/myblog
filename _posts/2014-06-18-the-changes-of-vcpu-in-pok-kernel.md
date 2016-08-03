---
layout: single
title: "The changes of vcpu in POK kernel"
modified:
categories: 
excerpt:
tags: []
image:
  feature:
  teaser: home.jpg
  thumb:
---

We have two choices, first, build the vcpu in extant files, or create new file to build vcpu.   
The vcpu is part of schedule in VMM, to manage the processor, and the arch-dependent structure (arch-vcpu) is relevant with current partition.   
As a result, first, the whole structure of vcpu is part of processor management, should be placed in kernel.   
I build a new file vcpu.h in kernel/include, and put the vcpu structure definition in it. Then build a arch_vcpu.h in kernel/arch/x86, and put the arch_vcpu in it. in this file, I use the context_t in this structure to contain user_regs.   
Also in the arch_vcpu, I put a interrupt_storeage struct, to store interrupt information.   
Then I builds a new file vcpu.c in kernel/core, and implement the alloc_vcpu function in this file. This function relies on some arch-dependent functions, like alloc_vcpu_struct and vcpu_initialize function. So I build a new file arch_vcpu.c in pok_kernel/arch/x86, and put the arch-dependent functions in.   
Also, I modify some file, like pok/kernel/include/core/partition.h. In this file, I planed to add a vcpu list head in partitions. Another file modified is kernel/core/sched.c, In this file, I add some empty function, because the schedule for vcpu is not necessary.   
Finally, I add the alloc_vcpu in partition_init.    
All the function will be test in this week.   

There is some thing need to note:   
1. the space alloced by alloc_vcpu_struct can not be free. So once the vcpu has been alloced, it can't be destroyed. As a result, the vcpu can be dynamic. So maybe we can alloc it in aadl file in the future.   
2. In the function vcpu_initialize, we planed to alloc schedule function, but as for now, the schedule for vcpu is not essential, so the function is empty for now.   
3. The function declarations in head files is omited in this blog.   

####Summary

#####New files
1. pok/kernel/core/vcpu.c
2. pok/kernel/arch/x86/arch_vcpu.c
3. pok/kernle/include/core/vcpu.h
4. pok/kernel/include/arch/x86/arch_vcpu.h

#####Modified files
1. pok/kernel/core/sched.c
2. pok/kernel/include/partition.h

#####Reused structure
1. The context_t is reused in arch_vcpu, to put the user_regs.
2. The interrupt_frame is reused in arch_vcpu, to put the interrupt information.

Part of the code is presented in github, but not all of them is commited.

Thank you very much, and if you got any problem please sent me an email <shenyouren@gmail.com>
