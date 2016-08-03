---
layout: single
title: "The current workflow of interrupt handling"
modified:
categories: 
excerpt:
tags: []
image:
  feature:
  teaser: home.jpg
  thumb:
---

##The workflow of current interrupt handling
![The work flow of interrupt handler in vCPU]({{site.img_url}}/The work flow of interrupt handler in vCPU.jpg)  
###The structure 
As usual, let's start with key structure:  
{% highlight C %}
struct vcpu
{ 
......
    /*
    * This bit will be set ture if there is a interrupt pending.
    */
   bool_t pending;
   arch_vcpu_t arch;
......
};
{% endhighlight %}

{% highlight C %}
typedef struct arch_vcpu
{
   /*
    * This struct contains the context of a vcpu, this part is arch-dependent.
    */
   vcpu_context_t  vcpu_context;
......

   /*
    * This is a interrupt frame, the interrupt information will be store in this struct;
    */
   struct irq_desc irqdesc[16];
   /*
    * Common interrupt hanler for Guest OS;
    */
   uint32_t handler;

}arch_vcpu_t;
{% endhighlight %}
{% highlight C %}
typedef struct irq_desc
{
   unsigned vector;
   bool_t pending;
   uint8_t counter;
}irq_desc_t;
{% endhighlight %}
{% highlight C %}
typedef struct vcpu_context
{
  interrupt_frame frame;
.......
}vcpu_context_t;
{% endhighlight %}
That's the key structure of vCPU related with interrupt handling.  
1. In the structure vcpu, there is a bit to mask whether there is a interrupt hanging in this vCPU or not.  
2. In the structure arch_vcpu, the handler is the common entry of Guest OS interrupt handling.  
3. In the structure arch_vcpu, the irq_desc arrays will record the interrupt register on this vCPU, and the counter in irq_desc will record the number this interrupt occurs.  
4. The interrupt frame in arch_vcpu will store the interrupt context.  
###The interrupt register function for vCPU   
See this [blog](http://huaiyusched.github.io/the-interrupt-register-function-for-vcpu/) please, thank you.  
This blog has been update in 7 August to fit newest code.  

###The design of upcall mechanism.
This is a difficult part, I have tried some way to implement it. But in this blog, I will not told you how I resolve it, I will only post the approaching for now.

####When all the things has been done of register and mask part, now the structure upon should be set as:   
1. The irq_desc, of course, is set with some interrupt, the vector reveal the number of the interrupt, and the counter reveal the time the interrupt happened.   
2. The handler in arch_vcpu, is set in pok_bsp_irq_register_vcpu, and the Guest pass the common entry of interrupt handling in Guest OS to pok_bsp_irq_register_vcpu.   
####What's the duty of upcall_irq?

The upcall_irq, as its name reveals, should notify the Guest OS about interrupt occurs. "up" means from Host OS to Guest OS; "call" means notify, call the Guest OS execute interrupt handler; and "irq" is a suffix, means interrupt related.   

####When the upcall will be invoked?
When the partition resumes, the hanging interrupt of this partition should be tickled. So:   
1. The corresponding partition resumes.   
2. One interrupt hanging in this vCPU.   

####What the upcall_irq exactly do?
{% highlight C %}
uint32_t upcall_irq(interrupt_frame* frame)
{
  struct vcpu *v;
  uint8_t i;
  uint32_t _eip;
  uint32_t user_space_handler;
  v = pok_partitions[POK_SCHED_CURRENT_PARTITION].vcpu;
  _eip = frame->eip;		// if no interrupt happened, return the point of normal program;
  user_space_handler = v->arch.handler;
  user_space_handler -= pok_partitions[POK_SCHED_CURRENT_PARTITION].base_addr;
  if(v->pending != 0)
  {
    for(i=0;i<15;i++)
    {
      if(v->arch.irqdesc[i].counter != 0)
      {
        save_interrupt_vcpu(v,frame);
        __upcall_irq(frame, i, (uint32_t) user_space_handler);
        v->arch.irqdesc[i].counter --;
	return user_space_handler;  //if any interrupt occours, return the point of interrupt handler;
      }
    }
  }
  return _eip;
}
{% endhighlight %}
1. Check the pending bit in vcpu, if it mask there is an interrupt hanging on it then go to step to.  
2. Check the irq_desc.  
3. If the counter not equal to zero, then save the interrupt context to interrupt frame, and invoke __upcall_irq.   

####What the __upcall_irq do?

The __some_function always be some core or assemble function of some_function. So the __upcall_irq is the key to understand the mechanism of it. 
So it'simportant to understand this function.  
{% highlight C %}
void __upcall_irq(interrupt_frame* frame,uint8_t vector, uint32_t handler)
{
  frame->eax = vector;        //put the irq number to eax
  frame->eip = handler;       //Set the eip as handler
}
{% endhighlight %}
Then it returns to common interrupt handler entry for Guest OS.

As you can see, the __upcall_irq will change the eax register as the vector of current interrupt. Also, a very very important step, change the eip register in stack for iret.

As we all know, the iret will resume the eip, cs, eflags from stack. so we change the eip in stack, and when the iret exert, the program will go as this eip point. What's this eip? The handler in vCPU. And the original eip is saved in save_interrupt_vcpu function. 

###The design of resume mechanism.
As we described, after the upcall_irq, we will use the iret return to common entry of Guest OS interrupt handling. After handle of interrupt, we should invoke HYPERCALL_IRQ_DO_IREQ. This hypercall will invoke do_iret in POK kernel. so we use the hypercall to change our into kernel space again.

####What the do_iret do?
{% highlight C %}
/*
 * This do_iret will check the irq_desc,and according to the irq_desc, construct interrupt frame, then iret to execute handler of Guest OS
 */
pok_ret_t do_iret(interrupt_frame *frame)
{
  struct vcpu *v;
  uint8_t i;
  uint32_t user_space_handler;

  v = pok_partitions[POK_SCHED_CURRENT_PARTITION].vcpu;

  user_space_handler = v->arch.handler;
  user_space_handler -= pok_partitions[POK_SCHED_CURRENT_PARTITION].base_addr;
  if(v->pending != 0)
  {
    for(i=0;i<15;i++)
    {
      while(v->arch.irqdesc[i].counter != 0)
      {
        __upcall_irq(frame, i, (uint32_t) user_space_handler);
	v->arch.irqdesc[i].counter--;
	return POK_ERRNO_OK;
      }
    }
    v->pending = 0;
  }
  else if(v->pending == 0)
  {
    restore_interrupt_vcpu(v, frame);
  }

  return POK_ERRNO_OK;
}
{% endhighlight %}
The do_iret is so like the upcall_irq. So let me introduce it briefly.   
The do_iret will check the pending bit and irq_desc structure, if there is no more interrupt hanging in this CPU, then resume the interrupt context from vCPU, if not, return to handler of Guest OS again.

If there is anything not clear, please contact me <shenyouren@gmail.com>
