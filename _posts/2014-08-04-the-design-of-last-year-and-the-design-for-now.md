---
layout: single
title: "The design of last year and the design for now"
modified:
categories: 
excerpt:
tags: []
image:
  feature:
  teaser: home.jpg
  thumb:
---

##The Interrupt handler of Philipp's design
1. Structure
The main structure of this design is meta_handler.
{%highlight C%}
struct meta_handler
{
  unsigned vector;
  /* POK_CONFIG_NB_PARTITIONS + KERNEL */
  void (*handler[POK_CONFIG_NB_PARTITIONS+1])(unsigned, void*);
  int waiting[POK_CONFIG_NB_PARTITIONS+1];
};
{% endhighlight %}

{%highlight C%}
static meta_handler handler_table[16];
{%endhighlight%}

The vector is this interrupt's vector. The handler is a point to the interrupt handler of Guest OS. This is dynamic register when Guest OS startup.

The meta_handler is created as static, which means the whole system share this structure to set interrupt.  
2. Register

When the POK register a interrupt which irq number great than 31 in kernel, the pok_arch_event_register while register a interrupt with handler pok_irq_prologue.

The handler of pok_irq_prologue is defined in interrupt_prologue.S. This function is defined as below:
{%highlight gas%}
#define DISTINCT_INTERRUPT_ENTRY(_vector)	  \
	.p2align 4				; \
	.globl pok_irq_prologue_ ## _vector 	; \
pok_irq_prologue_ ## _vector:		  \
	cli			      ; \
	subl  $4, %esp		      ; \
	pusha			      ; \
	push  %ds		      ; \
	push  %es		      ; \
        push  %esp		      ; \
	mov   $0x10, %ax	      ; \
        mov   %ax, %ds		      ; \
        mov   %ax, %es		      ; \
	movl  $ _vector, %eax	      ; \
	jmp   _ISR_Handler	      ; \


_ISR_Handler:
/* the IRQ vector number resides in EAX */
      push  %eax		      ; /* push vector number to stack */
      call  _C_isr_handler	      ; /* func expects the argument on the stack */
      
      pop   %ecx		      ; /* grab vector number from stack */
      
      call  update_tss		      ; /* update_tss with *frame */

      /* Cleanup stack*/

      addl  $4, %esp	      ; /* discard old stack pointer */
      pop   %es		      ;	/* remove interrupt_frame from stack */
      pop   %ds		      ; /* and restore old context */
      popa		      ;
      addl  $4, %esp	      ; /* remove error code  padding from stack */

      sti		      ; /* enable interrupts again */

      /* Acknowledging the interrupt must be done in the kernel handler code */
      iret		      ; /* return from interrupt */
{%endhighlight%}
As we can see, the call flow is pok_irq_prologue->_ISR_Handler->_C_isr_handler.Now the problem is that _C_isr_handler do not work.

{%highlight C%}
void _C_isr_handler( unsigned vector, interrupt_frame *frame ) 
{

  // If kernel handler registered 
  if( handler_table[vector].handler[POK_CONFIG_NB_PARTITIONS] != NULL )
    handler_table[vector].handler[POK_CONFIG_NB_PARTITIONS](vector, (void*)frame);


  // the following solution kills the cleanup and the update_tss code running
  // after the _C_isr_handler.
  // Stack is cleaned up and user space restored as far as necessary.
  
  if( partition_irq_enabled[POK_SCHED_CURRENT_PARTITION] == 0 )
  {
    if( handler_table[vector].handler[POK_SCHED_CURRENT_PARTITION] != NULL )
    {
      if( handler_table[vector].waiting[POK_SCHED_CURRENT_PARTITION] == 1 )
      {
	handler_table[vector].waiting[POK_SCHED_CURRENT_PARTITION] = 0; /* working on interrupt */
	update_tss(frame); /* needs to be done, as this path won't return to this handler */
	
	uint32_t user_space_handler = (uint32_t) handler_table[vector].handler[POK_SCHED_CURRENT_PARTITION];
	user_space_handler -= pok_partitions[POK_SCHED_CURRENT_PARTITION].base_addr;
	asm volatile(
	    /* move interrupt_frame parts to user space to be able to restore the
	     * interrupted context
	     */
	    "movl 56(%1), %%ebx	\t\n" //move user esp address to register

	    "movl 60(%1),	%%eax	\t\n"
	    "movl %%eax,	%%gs	\t\n" // move user's SS to gs register

	    "movl 44(%1), %%eax	\t\n" //move eip to register
	    "movl %%eax,	%%gs:(%%ebx)    \t\n" // move eip to user esp

	    "movl 36(%1), %%eax \t\n"
	    "movl %%eax,	%%gs:-4(%%ebx)  \t\n" //move eax to user esp

	    "movl 32(%1), %%eax \t\n" 
	    "movl %%eax,  %%gs:-8(%%ebx)  \t\n" // move ecx

	    "movl 28(%1), %%eax \t\n"
	    "movl %%eax,	%%gs:-12(%%ebx) \t\n" //move edx

	    "movl 24(%1), %%eax \t\n"
	    "movl %%eax,  %%gs:-16(%%ebx) \t\n" //move ebx

	    "movl 20(%1), %%eax \t\n"
	    "movl %%eax,	%%gs:-20(%%ebx) \t\n" //move __esp

	    "movl 16(%1), %%eax \t\n"
	    "movl %%eax,	%%gs:-24(%%ebx) \t\n" //move ebp

	    "movl 12(%1), %%eax \t\n"
	    "movl %%eax,	%%gs:-28(%%ebx) \t\n" //move esi

	    "movl 8(%1),  %%eax \t\n"
	    "movl %%eax,	%%gs:-32(%%ebx) \t\n" //move edi 

	    /* don't move ds and es, as they are already restored before the switch
	     * to user space and are not touched by popa */
	    /* prepare the user space stack to look like a propper function call */

	    "movl %0,	    %%gs:-36(%%ebx) \t\n" //arg1

	    "movl $0xffeeddcc, %%eax \t\n" // MAGIC NUMBER -> searched for in user space handler
	    "movl %%eax,	    %%gs:-40(%%ebx) \t\n"

	    "movl 56(%1),	    %%eax \t\n"
	    "sub	$44,	    %%eax	    \t\n" // update esp in frame
	    "movl %%eax,	    56(%1)	    \t\n"

	    /* prepare segment registers for switch to user space */

	    "movl 4(%1),  %%eax	  \t\n" //move ds to eax
	    "movl (%1),   %%ebx	  \t\n"	//move es to eax
	    "mov %%ax,    %%ds	  \t\n"
	    "mov %%ax,    %%fs	  \t\n"
	    "mov %%ax,    %%gs	  \t\n"
	    "mov %%bx,    %%es	  \t\n"

	    /* prepare stack for iret with user space values saved in interrupt
	     * frame*/
	    /* TODO BOGUS if interrupt occurres in kernel space, must be checked! */

	    /* delete interrupt frame from stack */
	    "movl %1, %%eax \t\n"  // move frame pointer to eax
	    "add $44, %%eax \t\n" //  add 44 to the frame pointer
	    "movl %%eax, %%esp \t\n" //delete everything on the stack except eip,cs,eflags,esp,ss

	    //	Enable/Disable interrupts at iret for testing purpose.
	    //	"movl 8(%%esp), %%eax \t\n"   // grab eflags from stack
	    //	"xor $0x200, %%eax \t\n"	      // set IF flag aka enable interrupts
	    //	"movl %%eax, 8(%%esp) \t\n"  // push eflags back

	    /* change eip address to user space handler address */
	    "movl %2, (%%esp) \t\n"

	    "iret		  \t\n"
	    :
	    : "r"(vector), "r"(frame), "r"(user_space_handler)
	    : "%eax", "%ebx"
	      );
	/*
	 *  NOT REACHED!
	 */
      }
      /* REACHED if interrupt occurres but partition isn't ready for it */
    }
  }
}
{%endhighlight%}

This _C_isr_handler is very very long, but we can separate it as two part clearly. First C part, choose the handler from meta_handler, and calculate the right address of user space handler. The second is assemble part. In this part, we want to emulate the interrupt frame in user space, and then using the iret function to return to user function to execute the interrupt handler of Guest OS. However, this part did not work, especially the iret will generate a fault.


###My Design for now:

Firstly when interrupt occurs, the handler in POK kernel will mark the vCPU, and then in the pok_sched, when the partition resumes, the upcall_irq function will check the vCPU of current partition, then trying to running the handler of guest OS.   
Now we are facing the same problem. The upcall_irq is invoked in kernel space. But the handler of guest OS should be invoke in privilege 3. So the problem is how to back to user space to running the handler.  
The way return to user space in pok_sched to execute the handler is impractical. Because this will make the pit_interrupt so heavy. So we have to using a mechanism to mark it, and when in the user space, we invoke the handler alread be upcall before.  
Or we can use the hypercall to transfer the handler into kernel space.But this way obviously make the kernel insecure. Also, we can using another thread to execute the handler those are invoked. 
