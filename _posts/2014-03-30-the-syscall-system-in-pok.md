---
layout: single
title: "The syscall system in POK and interrupt handler in POK"
modified:
categories: 
excerpt:
tags: []
image:
  feature:
  teaser: home.jpg 
  thumb:
---

####Focus on interrupt_frame
The definition of interrupt_frame is:

{% highlight C %}
typedef struct
{
  uint32_t es;
  uint32_t ds;
  uint32_t edi;
  uint32_t esi;
  uint32_t ebp;
  uint32_t __esp;
  uint32_t ebx;
  uint32_t edx;
  uint32_t ecx;
  uint32_t eax;

  /* These are pushed by interrupt */
  uint32_t error;	/* Error code or padding */
  uint32_t eip;
  uint32_t cs;
  uint32_t eflags;

  /* Only pushed with privilege switch */
  /* (Check cs content to have original CPL) */
  uint32_t esp;
  uint32_t ss;
} interrupt_frame;
{% endhighlight %}

But when we define a object and fill it?

The answer is that we do not define a real object and fill it when interrupt happens.
The interrupt_frame is designed to save the processor current.We push all the register to stack, and the ESP register is used to point the top of the stack,and when we push a operand into stack, the esp will decrease since the stack in x86 grows down.
So, when we call the syscall_gate_handler, we just need to use the esp as the address of interrupt_frame, then we can refer the variables we pushed before.

####More details of syscall_gate
As we can see, the int 42 will invoke syscall_gate, then the syscall_gate will invoke the syscall_gate_handler:

{% highlight C %}
void syscall_gate_handler(interrupt_frame* frame)
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

The syscall_gate_handler get informations from the interrupt_frame and then invoke the pok_core_syscall.
In the pok_core_syscall, the POK will invoke corresponding handler of the syscall id, and the syscall id is coming from the interrupt_frame and assigned before invoke syscall.

####The changes in POK kernel.
I'd like to divide the CPU paravirtualization into two parts. One is to replace the privilege instructions, the other to implement the interrupt handler to guest.For the first part, Philipp has design and implement the framework. For the other part, the Philipp has suffer some problem and, now I have to read this part of code and know the reason why the mechanism is faulty.

The first part belongs to RTEMS, and if we want to implement more function, we have to replace more instructions using syscall or hypercall, but not just only some dummy functions.

As we discuss [before](http://huaiyusched.github.io/pok-startup-flow-and-interrupt-system/), the interrupt system consisting of two parts, one's vector number is less than 32, which is reserved by INTES, and initialized with series exception_list, the other's vector number is great than 32, which can be use liberalized. 

Now let's turn bake to the topic, What's the change in POK kernel?

{% highlight C %}
pok_ret_t pok_bsp_init (void)
{
   pok_cons_init ();
   pok_pm_init ();
   pok_pic_init ();
   *pok_meta_handler_init();*
   *pok_partition_irq_init();*

   return (POK_ERRNO_OK);
}
{% endhighlight %}

The pok_meta_handler_init and the pok_partition_irq_init is added by us. "'pok_meta_handler_init'sets up the software-IDT and fills all fields with start values (magic unused vector number, no handler present, but waiting).'pok_partition_irq_init' sets up partition_irq_enabled table with the value for disabled (0), so initially no partition gets interrupts until it asks for them.", Said by Philipp.

To using the liberalized interrupted number, we have to extend the pok_arch_event_register:

{% highlight diff %}
 pok_ret_t pok_arch_event_register  (uint8_t vector,
                                     void (*handler)(void))
 {
-   pok_idt_set_gate (vector,
+  if( vector > 31 && vector < 48 ) /* first 32 lines reserved by intel */
+  {
+    pok_idt_set_gate (vector,
+                     GDT_CORE_CODE_SEGMENT << 3,
+        (uint32_t) pok_irq_prologue[vector - 32], /* to fit the prologue array */
+                     IDTE_TRAP,
+                     3);
+
+    return (POK_ERRNO_OK);
+  }
+  else
+  {
+    pok_idt_set_gate (vector,
                      GDT_CORE_CODE_SEGMENT << 3,
-                     (uint32_t)handler,
+        (uint32_t) handler,
                      IDTE_TRAP,
                      3);
 
-   return (POK_ERRNO_OK);
+    return (POK_ERRNO_OK);
+  }
 }
{% endhighlight %}

For example, when the timer initialized, we just invoke the pok_bsp_irq_register_hw->pok_arch_event_register.The pok_bsp_irq_register_hw will judge if the irq handler is from kernel or partitions.Finally, the pok_arch_event_register will set corresponding pok_irq_prologue and vector with clock.
When the clock interrupt occurs, the corresponding pok_irq_prologue will invoke, and invoke the _ISR_Handler, then invoke the _C_isr_handler and iret.(which failed)

####Conclusion
As I said before, I'd like to divide the paravirtualization into two parts, one is using the hypercall to implement virtualization layer in RTEMS, the other is handling interruptions in POK. Now we use the meta_handler to register an ISR in POK, but we failed to return to user space. I'm just wondering that whether we can devide the interruptions to two parts, one is the kernel interruption, the other is guest interruption. we can deal with the kernel interruptions in Kernel space, and dispatch the guest interruptions to partitions.

Another confusion is when the interruption occurs, why we should notify the partitions as soon as possible?
