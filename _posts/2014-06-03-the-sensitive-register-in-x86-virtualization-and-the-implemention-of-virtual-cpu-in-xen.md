---
layout: single
title: "The sensitive register in X86 virtualization and the implemention of virtual cpu in XEN"
modified:
categories: 
excerpt:
tags: []
image:
  feature:
  teaser: home.jpg
  thumb:
---
In my views, there is no such concept called sensitive register in x86 platform. Although the x86 privilege model is beneficial for virtualization, the sensitive instructions of x86 virtualization is very complicated. The part of reason is because many sensitive instruction will have different performance in kernel and user model. That is say, there are some register, to access them in different privileges may cause different reflection. So, there is a set of sensitive instructions called **Sensitive register instructions**.   
I will abstract the sensitive register from this Sensitive register instructions.

####The sensitive register and sensitive register instructions
Let's distinguish two key concepts first: **sensitive** and **privilege**.   
When we describe a instruction sensitive means it will cause wrong results when the guest OS running it as native OS. And the privilege instructions always needs privilege to execute, or else will cause a fault in x86 system. Apparently, every privilege instruction is sensitive instruction.   

1. SGDT, SIDT, SLDT   
According to the Intel® 64 and IA-32 Architectures Software Developer’s Manual, the SGDT (Store Global Descriptor Table), SIDT (Store Interrupt Descriptor Table), SLDT (Store Local Descriptor Table) are not privilege instructions itself. That is say, they are sensitive but not privilege. However, The function of these instructions are store some real and unique register to memory. For the guest OS, the value of these register is apparent wrong, also when more then one partitions try to use the same register, it apparent get wrong value. So, on the traditional VMM, we fake some virtual registers, then replace these instructions with some functions returning the virtual register.   
However, these register is mostly for virtualization memory management.

2. SMSW   
The SMSW (Store Machine Status Word) instruction store the CR0[0:15] to a register or memory. Just like SGDT, the SMSW is not a privilege instruction itself, but using it in guest OS will return the real machine register, which is wrong for guest OS. Like SGDT, this sensitive instruction is not privilege.   
We should fake a Machine Status Word register (CRx in x86 platform.)

3. PUSHF, POPF   
PUSHF (Push EFLAGS Register onto the Stack) and POPF (Pop stack into EFLAGS Register) is a couple of opposite instructions. The PUSHF read the real machine register to stack while the POPF pop a stack value to real machine register. As a result, there are two issues. On the one hand, like SMSW, we have to fake register for Guest OS, on the other hand, the POPF needs more authority to invoke. I.e. they are privilege instruction.

According to the discussion upon, this is all of **sensitive register** in x86 platform.  
- LDTR  
- IDTR  
- GDTR  
- CR[0]  
- EFLAGS  

How ever it's `definitely not enough` to build a vcpu in paravirtualization.

####The vcpu structure in XEN.
The source code is come from XEN 4.0.4, and the complete code is so long and I will just put the necessary information for now. The symbol `......`means there are some code is omitted.

Firstly, the structure vcpu.
{% highlight C %}
struct vcpu 
{
    int              vcpu_id; 
    int              processor;
    vcpu_info_t     *vcpu_info;
    struct domain   *domain;
    struct vcpu     *next_in_list;
...... info of schedule.
...... extra info about fpu.

    /* IRQ-safe virq_lock protects against delivering VIRQ to stale evtchn. */
    u16              virq_to_evtchn[NR_VIRQS];
    spinlock_t       virq_lock;

    /* Bitmask of CPUs on which this VCPU may run. */
    cpumask_t        cpu_affinity;
    /* Used to change affinity temporarily. */
    cpumask_t        cpu_affinity_tmp;

    /* Bitmask of CPUs which are holding onto this VCPU's state. */
    cpumask_t        vcpu_dirty_cpumask;

    struct arch_vcpu arch;
};
{% endhighlight %}
Then let's trace the arch_vcpu.
{% highlight C %}
struct arch_vcpu
{
    /* Needs 16-byte aligment for FXSAVE/FXRSTOR. */
    struct vcpu_guest_context guest_context
    __attribute__((__aligned__(16)));

    struct pae_l3_cache pae_l3_cache;

    unsigned long      flags; /* TF_ */
...... schedule info.

 /* Bounce information for propagating an exception to guest OS. */
    struct trap_bounce trap_bounce;

...... I/O info.


    /* Virtual Machine Extensions */
    struct hvm_vcpu hvm_vcpu;

...... shadow page info.

    struct paging_vcpu paging;

......

} __cacheline_aligned;
{% endhighlight %}

Then let's trace down to the vcpu_guest_context.

{% highlight C %}
struct vcpu_guest_context {
    /* FPU registers come first so they can be aligned for FXSAVE/FXRSTOR. */
    struct { char x[512]; } fpu_ctxt;       /* User-level FPU registers     */
...... Some macro.
    unsigned long flags;                    /* VGCF_* flags                 */
    struct cpu_user_regs user_regs;         /* User-level CPU registers     */
    struct trap_info trap_ctxt[256];        /* Virtual IDT                  */
    unsigned long ldt_base, ldt_ents;       /* LDT (linear address, # ents) */
    unsigned long gdt_frames[16], gdt_ents; /* GDT (machine frames, # ents) */
    unsigned long kernel_ss, kernel_sp;     /* Virtual TSS (only SS1/SP1)   */
    /* NB. User pagetable on x86/64 is placed in ctrlreg[1]. */
    unsigned long ctrlreg[8];               /* CR0-CR7 (control registers)  */
    unsigned long debugreg[8];              /* DB0-DB7 (debug registers)    */
...... Some call back sign.
};
{% endhighlight %}

lastly let's have a look to cpu_user_regs.

{% highlight C %}
struct cpu_user_regs {
    uint32_t ebx;
    uint32_t ecx;
    uint32_t edx;
    uint32_t esi;
    uint32_t edi;
    uint32_t ebp;
    uint32_t eax;
    uint16_t error_code;    /* private */
    uint16_t entry_vector;  /* private */
    uint32_t eip;
    uint16_t cs;
    uint8_t  saved_upcall_mask;
    uint8_t  _pad0;
    uint32_t eflags;        /* eflags.IF == !saved_upcall_mask */
    uint32_t esp;
    uint16_t ss, _pad1;
    uint16_t es, _pad2;
    uint16_t ds, _pad3;
    uint16_t fs, _pad4;
    uint16_t gs, _pad5;
};
{% endhighlight %}

So, in my opinion, if we want to implement a virtual cpu, the important is the cpu context. it not enough if we only get some sensitive register in implemention.

If you got interest, track this flow: 
schedule()  
|-- context_switch(prev, next)  
| |-- __context_switch  
| | |-- vcpu->arch.ctxt_switch_from(prev)  
| | |-- vcpu->arch.ctxt_switch_to(next)  
| |-- load_LDT  
| |-- load_segments  
| | |-- load “guset context” from VCPU  
| |-- schedule_tail(next)  

####Summary
As we discussed, there are some sensitive instruction, and some sensitive register too, but maybe the concept sensitive register is not useful. Because, first, only fake the sensitive register is not enough to implement a virtual cpu. The context is essential for a cpu. Second, some sensitive instruction, like POP, it's privilege related, for example, when it pop to a register, it needs to check DPL and CPL first, in this situation, every segment register need corresponding privilege to access.

If we want to implement a vcpu, just implement the context of it, and then implement some hypercall corresponding to sensitive instruction.
