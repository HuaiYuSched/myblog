---
layout: single
title: "POK startup flow and interrupt system"
modified:
categories: 
excerpt:
tags: []
image:
  feature:
  teaser: home.jpg
  thumb:
---

    Beauty is more important in computing than anywhere else in technology because software is so complicated. Beauty is the ultimate defence against complexity.
                                                                                — David Gelernter
After you reading this post, you will find the pok kernel is so graceful and beautiful. So, let's do it. 
####Start from link script.

The link script which is located in directory $POK_PATH/misc/ldscripts/x86/x86-qemu defined the start addr of POK kernel and partitions, also will assign a ENTRY point for the whole kernel elf file.

So let's first take a look at kernel.lds
{% highlight c %}
OUTPUT_FORMAT("elf32-i386");
OUTPUT_ARCH("i386")
ENTRY(_core_entry)

SECTIONS
{
	. = 0x100000;

	__pok_begin = . ;

	.text :
	{
		*(.multiboot)
		*(.text)
	}

	.rodata :
	{
		*(.rodata)
	}

	.data :
	{
		*(.data) *(.bss) *(COMMON)

		__archive_begin = .;
		*(.archive)
		__archive_end = .;
		__archive2_begin = .;
		*(.archive2)
		__archive2_end = .;
	}

	__pok_end = . ;
}
{% endhighlight %}

First, the script define the output format as elf on x86 platform.Then the _core_entry function was defined as entry point, which means when the POK startup, The _core_entry function will be execute firstly.

The point "." symbol means current address in linux scripts. So the POK kernel defined the start address of the first section as 0x100000. Then this script defined a variable names _pok_begin to mark this address.

After that, There are three section definition text, and notice the __pok_end since we will use it in the partition initiation. Apparently, the _pok_end is a mark of end of pok kernel. 

####Next: the entry point.

As we can see from the link scripts, The entry point is the _core_entry, which is in the file $POK_PATH/kernel/arch/x86/x86-qemu/entry.S.
{% highlight gas %}
core_entry:
_core_entry:
	movl $(pok_stack + STACK_SIZE - 4), %ebp
	movl %ebp, %esp

	/* Set EFLAGS to 0 */
	pushl $0
	popf

	mov %eax, pok_multiboot_magic
	mov %ebx, pok_multiboot_info

	call pok_boot
loop:
	hlt
	jmp loop
{% endhighlight %}

The _core_entry really did not do many things beside the initialization of stack and assignment of some multiboot variable. Finally, the _core_entry invoke the function pok_boot.

####Nearly end but most important

In my side, The pok_boot function in POK kernel is similar with the start_kernel in Linux in some extent. Both of them invoke the functions of initialization in their kernel.


{% highlight c%}
void pok_boot ()
{
   pok_arch_init();
   pok_bsp_init();

#if defined (POK_NEEDS_TIME) || defined (POK_NEEDS_SCHED) || defined (POK_NEEDS_THREADS)
   pok_time_init();
#endif

#ifdef POK_NEEDS_PARTITIONS
   pok_partition_init ();
#endif

#ifdef POK_NEEDS_THREADS
   pok_thread_init ();
#endif

#if defined (POK_NEEDS_SCHED) || defined (POK_NEEDS_THREADS)
   pok_sched_init ();
#endif

......

#if defined (POK_NEEDS_DEBUG) || defined (POK_NEEDS_CONSOLE)
  pok_cons_write ("POK kernel initialized\n", 23);
#endif

......

  pok_arch_preempt_enable();

#ifndef POK_NEEDS_PARTITIONS
  /**
   * If we don't use partitioning service, we execute a main
   * function. In that case, POK is acting like an executive,
   * not a real kernel
   */
  main ();
#endif
}
{% endhighlight %}


Then we should look at the function behind line by line. 
The pok_arch_init:
{% highlight c %}
pok_ret_t pok_arch_init ()
{
  pok_gdt_init ();
  pok_event_init ();

  return (POK_ERRNO_OK);
}
{% endhighlight %}

It seems simply easy, right? So Let's check out the pok_gdt_init. 

{% highlight c %}
pok_ret_t pok_gdt_init()
{
   sysdesc_t sysdesc;

   /* Set null descriptor and clear table */
   memset(pok_gdt, 0, sizeof (gdt_entry_t) * GDT_SIZE);

   /* Set kernel descriptors */
   gdt_set_segment(GDT_CORE_CODE_SEGMENT, 0, ~0UL, GDTE_CODE, 0);
   gdt_set_segment(GDT_CORE_DATA_SEGMENT, 0, ~0UL, GDTE_DATA, 0);

   /* Load GDT */
   sysdesc.limit = sizeof (pok_gdt);
   sysdesc.base = (uint32_t)pok_gdt;

   asm ("lgdt %0"
         :
         : "m" (sysdesc));

   /* Reload Segments */
   asm ("ljmp %0, $1f	\n"
         "1:		\n"
         "mov %1, %%ax	\n"
         "mov %%ax, %%ds	\n"
         "mov %%ax, %%es	\n"
         "mov %%ax, %%fs	\n"
         "mov %%ax, %%gs	\n"
         "mov %%ax, %%ss	\n"
         :
         : "i" (GDT_CORE_CODE_SEGMENT << 3),
         "i" (GDT_CORE_DATA_SEGMENT << 3)
         : "eax");

   pok_tss_init();

   return (POK_ERRNO_OK);
}
{% endhighlight %}

1. At the first we define a array named as pok_gdt to store the GDT and a sysdesc to memorize GDTR.
2. Initialize the pok_gdt, using the memset to set every bit in array pok_gdt as 0.
3. Set the first node(in fact is second node, index is 1, and the real first node in gdt(which index is zero) is dummy, So I'd like to ignore it) in pok_gdt as base=0, limit=0xffffffff, type = CODE, and DPL=0.
Then set second node in pok_gdt as base=0, limit=0xffffffff, type = DATA, and DPL=0.
4. Set the sysdesc as the pok_gdt's size and base address, then using the lgdt instruction to set GDTR.
5. This is very important.The inline assembly is not easy to read, So I translated it to real assembly.
{% highlight objdump %}
  1024b7:   ea be 24 10 00 08 00 	ljmp   $0x8,$0x1024be
  1024be:	66 b8 10 00          	mov    $0x10,%ax
  1024c2:	8e d8                	mov    %eax,%ds
  1024c4:	8e c0                	mov    %eax,%es
  1024c6:	8e e0                	mov    %eax,%fs
  1024c8:	8e e8                	mov    %eax,%gs
  1024ca:	8e d0                	mov    %eax,%ss
{% endhighlight %}

the first line "ljmp $0x8,$021024be" is tring to jump to the GDT_CORE_CODE_SEGMENT(0x8) with offset $0x1024be.
that is say, although this line is just jump to next line, but it set the cs as GDT_CORE_CODE_SEGMENT.
Then the POK kernel set all ds,es,fs,gs,ss as GDT_CORE_DATA_SEGMENT.

Here is the GDT initialization.Next is IDT initialization.
{% highlight c %}
pok_ret_t pok_event_init ()
{
   pok_idt_init ();

#if defined (POK_NEEDS_DEBUG) || defined (POK_NEEDS_ERROR_HANDLING)
   pok_exception_init ();
#endif

   pok_syscall_init ();

   return (POK_ERRNO_OK);
}
{% endhighlight %}

Aha, as we can see, in the pok_event_init, the POK initialized all kind of interrupt, exception, and syscall.
So Let's take a more closer look.
OK, take it easy, the IDT initialization is so similar with GDT, so it won't be difficult.
{% highlight c %}
pok_ret_t pok_idt_init ()
{
   sysdesc_t sysdesc;

   /* Clear table */
   memset(pok_idt, 0, sizeof (idt_entry_t) * IDT_SIZE);

   /* Load IDT */
   sysdesc.limit = sizeof (pok_idt);
   sysdesc.base = (uint32_t)pok_idt;

   asm ("lidt %0"
        :
        : "m" (sysdesc));

  return (POK_ERRNO_OK);
}
{% endhighlight %}

You see, It initialize the IDTR just like initialize the GDTR before.

{% highlight c %}
pok_ret_t pok_exception_init()
{
  int i;

  for (i = 0; exception_list[i].handler != NULL; ++i)
  {
    pok_idt_set_gate (exception_list[i].vector,
		                GDT_CORE_CODE_SEGMENT << 3,
                      (uint32_t) exception_list[i].handler,
                      IDTE_INTERRUPT,
                      3);
  }

  return (POK_ERRNO_OK);
}
{% endhighlight %}

Here we go, to guess the effect of this function is really easy, initialize the exception handler by pok_idt_set_gate.
But to understand it completely, we have to look this struct first.

{% highlight c %}
static const struct
{
  uint16_t	vector;
  void		(*handler)(void);
}
exception_list[] =
{
  { EXCEPTION_DIVIDE_ERROR, exception_divide_error},
  { EXCEPTION_DEBUG, exception_debug},
  { EXCEPTION_NMI, exception_nmi},
  { EXCEPTION_BREAKPOINT, exception_breakpoint},
  { EXCEPTION_OVERFLOW, exception_overflow},
  { EXCEPTION_BOUNDRANGE, exception_boundrange},
  { EXCEPTION_INVALIDOPCODE, exception_invalidopcode},
  { EXCEPTION_NOMATH_COPROC, exception_nomath_coproc},
  { EXCEPTION_DOUBLEFAULT, exception_doublefault},
  { EXCEPTION_COPSEG_OVERRUN, exception_copseg_overrun},
  { EXCEPTION_INVALID_TSS, exception_invalid_tss},
  { EXCEPTION_SEGMENT_NOT_PRESENT, exception_segment_not_present},
  { EXCEPTION_STACKSEG_FAULT, exception_stackseg_fault},
  { EXCEPTION_GENERAL_PROTECTION, exception_general_protection},
  { EXCEPTION_PAGEFAULT, exception_pagefault},
  { EXCEPTION_FPU_FAULT, exception_fpu_fault},
  { EXCEPTION_ALIGNEMENT_CHECK, exception_alignement_check},
  { EXCEPTION_MACHINE_CHECK, exception_machine_check},
  { EXCEPTION_SIMD_FAULT, exception_simd_fault},
  { 0, NULL}
};
{% endhighlight %}

Here we defined a list of struct named exception_list. every exception in the list has a vector and a handler relate to the function dealing with the exception corresponded.
Now we turn back to see the pok_exception_init, we just set every exception handler to IDT by using pok_idt_set_gate. And the handler is defined in exception_list.
{% highlight c %}
/**
 * Init system calls
 */
pok_ret_t pok_syscall_init ()
{
   pok_idt_set_gate (POK_SYSCALL_INT_NUMBER,
                     GDT_CORE_CODE_SEGMENT << 3,
                     (uint32_t) syscall_gate,
                     IDTE_INTERRUPT,
                     3);

   return (POK_ERRNO_OK);
}
{% endhighlight %}

Now, in the pok_syscall_init, we just set the syscall entry point as index=42, handler=syscall_gate.

Now, this part is not easy to understand as before. I will take it slowly.

To begin with, where is the syscall_gate defined? 

{% highlight c %}
INTERRUPT_HANDLER_syscall(syscall_gate)
{% endhighlight %}

The INTERRUPT_HANDLER_syscall is a macro defined in the file $POK_PATH/kernel/include/arch/x86/interrupt.h
{% highlight c %}
#define INTERRUPT_HANDLER_syscall(name)						\
int name (void);							\
void name##_handler(interrupt_frame* frame);				\
  asm (	    			      			      		\
      ".global "#name "			\n"				\
      "\t.type "#name",@function	\n"				\
      #name":				\n"				\
      "cli			\n"				\
      "subl $4, %esp			\n"				\
      "pusha				\n"				\
      "push %ds				\n"				\
      "push %es				\n"				\
      "push %esp			\n"				\
      "mov $0x10, %ax			\n"				\
      "mov %ax, %ds			\n"				\
      "mov %ax, %es			\n"				\
      "call " #name"_handler		\n"				\
      "movl %eax, 40(%esp)         \n" /* return value */  \
      "call update_tss			\n"				\
      "addl $4, %esp			\n"				\
      "pop %es				\n"				\
      "pop %ds				\n"				\
      "popa				\n"				\
      "addl $4, %esp			\n"				\
      "sti			\n"				\
      "iret				\n"				\
      );								\
void name##_handler(interrupt_frame* frame)
{% endhighlight %}

The fisrt two lines are two declaration of functions syscall_gate and syscall_gate_handler.
The asm block defines the functions syscall_gate,which will do some saving job and change the cs to kernel segment, then it will call syscall_gate_handler.
As we can see, the last line of this macro is a definition of syscall_gate_handler, which will followe by the code we see in sycalls.c:

{% highlight c %}
INTERRUPT_HANDLER_syscall(syscall_gate)
{
   pok_syscall_info_t   syscall_info;
   pok_ret_t            syscall_ret;
   pok_syscall_args_t*  syscall_args;
   pok_syscall_id_t     syscall_id;

   /*
    * Give informations about syscalls: which partition, thread
    * initiates the syscall, the base addr of the partition and so on.
    */
   syscall_info.partition = PARTITION_ID (frame->cs);
   syscall_info.base_addr = pok_partitions[syscall_info.partition].base_addr;
   syscall_info.thread    = POK_SCHED_CURRENT_THREAD;

   syscall_args = (pok_syscall_args_t*) (frame->ebx + syscall_info.base_addr);

   /*
    * Get the syscall id in the eax register
    */
   syscall_id = (pok_syscall_id_t) frame->eax;

   /*
    * Check that pointer is inside the adress space
    */
   if (POK_CHECK_PTR_IN_PARTITION(syscall_info.partition, syscall_args) == 0)
   {
         syscall_ret = POK_ERRNO_EINVAL;
   }
   else
   {
      /*
       * Perform the syscall baby !
       */
      syscall_ret = pok_core_syscall (syscall_id, syscall_args, &syscall_info);
   }

   /*
    * And finally, put the return value in eax register
    */
   asm ("movl %0, %%eax  \n"
	:
	: "m" (syscall_ret));
}
{% endhighlight %}

This function is important too, but I don't want a such long post. As a result, I will discuss it next week.
we just need to know the architecture of syscall now.

Finally we finished the discuss of pok_arch_init. And we have a overview of the architecture of interrupt system in POK.
I'd like to discuss the syscall in more details, and the changes we have alreadly done in pok kernel interrupt system.

If I got anything wrong or you have any problem, Please feel free to comment of send me a email shenyouren@gmail.com. 
