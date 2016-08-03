---
layout: single
title: "Separate the POK X86 BSP to x86 qemu and x86 qemu vmm"
modified:
categories: 
excerpt:
tags: []
image:
  feature:
  teaser: home.jpg
  thumb:
---

Separate the POK BSP to x86-qemu and x86-qemu-vmm
#####Change in POK
To separate the POK BSP to x86-qemu and x86-qemu-vmm will benefit to the paravirtualization, on the point that the change of x86-qemu-vmm will not influence the normal x86-qemu, and also the change of x86-qemu-vmm will be more clear.

Where to change:
The most change of paravirtualization in last year is located in the three files, that is kernel/arch/x86/x86-qemu/bsp.c kernel/arch/x86/interrupt_prologue.S and kernel/arch/x86/interrupt.h

So at first, Philipp build a new BSP named x86-qemu-vmm, and move the jobs have been done last year, also change the ocarina -- the tools to build the pok application automatically -- to be able to build the x86-qemu-vmm. Also, Philipp use the macro POK_NEEDS_X86_VMM to guard some interrupt build for paravirtualizaiton.

The change beyond is independent with other BSP, but the change in interrupt_prologue.S will influence all the BSP in x86 folder, also I want the x86-qemu will perform with no influence of paravirtualization, so we using the Macro POK_NEEDS_X86_VMM to separate it.

In arch.c, the function pok_arch_event_register derive to types, one is for x86-qemu, the other, of course is for x86-qemu-vmm.  
{% highlight diff %}
diff --git a/kernel/arch/x86/arch.c b/kernel/arch/x86/arch.c
index 917f3f3..1d54dda 100644
--- a/kernel/arch/x86/arch.c
+++ b/kernel/arch/x86/arch.c
@@ -58,6 +58,7 @@ pok_ret_t pok_arch_idle()
 }
 
 
+#ifdef POK_NEEDS_X86_VMM
 extern void pok_irq_prologue_0(void);
 extern void pok_irq_prologue_1(void);
 extern void pok_irq_prologue_2(void);
@@ -119,6 +120,20 @@ pok_ret_t pok_arch_event_register  (uint8_t vector,
   }
 }
 
+#else
+pok_ret_t pok_arch_event_register  (uint8_t vector,
+                                    void (*handler)(void))
+{
+  pok_idt_set_gate (vector,
+                   GDT_CORE_CODE_SEGMENT << 3,
+      	     (uint32_t) handler,
+                   IDTE_TRAP,
+                   3);
+
+  return (POK_ERRNO_OK);
+}
+#endif /* POK_NEEDS_X86_VMM */
+
 uint32_t    pok_thread_stack_addr   (const uint8_t    partition_id,
                                      const uint32_t   local_thread_id)
 {
{% endhighlight diff %}
Also the interrupt_prologue.S is for x86-qemu-vmm only, so we also change the Makefile in kernel/arch/x86/ to separate it: see below:
{% highlight diff %}
diff --git a/kernel/arch/x86/Makefile b/kernel/arch/x86/Makefile
index c486d47..f9cba01 100644
--- a/kernel/arch/x86/Makefile
+++ b/kernel/arch/x86/Makefile
@@ -13,10 +13,14 @@ LO_OBJS=	arch.o		\
 			space.o		\
 			syscalls.o	\
 			interrupt.o	\
-			interrupt_prologue.o	\
 			pci.o		\
 			exceptions.o
 
+ifeq ($(BSP),x86-qemu-vmm)
+
+LO_OBJS+= interrupt_prologue.o
+
+endif
 LO_DEPS=	$(BSP)/$(BSP).lo
 
 all: $(LO_TARGET)
{% endhighlight diff %}   
Now I hope it's clear enough, and the change will be used in the next step: to build the hypercall system.   
Also, if you got any problem or any suggestion, please feel free to tell me.  
#####Outline 
There are five weeks to midterm, so here is my outline until midterm:  
   1. I will implement the most of work of framework of hypercall, ie.,the basic system of hypercall before next week.   
   2. Implement some hypercall with specific sensitive instructions like cli, and also using them in paravirtualization layer.   
   3. Adapt the meta_handler to be workable with the register operation. which includes to add some flags to make the interrupt attribution and the corresponding partition.   
   4. Implement the register interrupt operation in paravirtualization layer.   
   5. Maybe the Schedule needs some flexibility :).    
