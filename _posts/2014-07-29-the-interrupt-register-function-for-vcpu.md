---
layout: single
title: "The interrupt register function for vCPU"
modified:
categories: 
excerpt:
tags: []
image:
  feature:
  teaser: home.jpg
  thumb:
---

Last series of weeks I developed an interrupt register function in vCPU. This implementation which contains three parts in POK kernel.   
1. adapt the vCPU structure to be able to mask the interrupt register and handling.  
2. Add register function in hypercall system.  
3. Add do_IRQ function in POK interrupt handler, this function will check the IRQ and vCPU structure, to see whether the interrupt is register in corresponding vCPU. If yes, then mask and add the counter in vCPU structure.   

So let's see the code in details:  
####The structure of vCPU 
{% highlight C %}
typedef struct arch_vcpu
{
   ......

   /*
    * This is a interrupt frame, the interrupt information will be store in this struct;
    */
   struct irq_desc irqdesc[16];

}arch_vcpu_t;

typedef struct irq_desc
{
   unsigned vector;
   uint8_t counter;
}irq_desc_t;
{% endhighlight %}

As we can see, the arch_vcpu include an array of irq_desc_t, this structure is only for vCPU interrupt handling. There is no relation between this structure and POK physical interrupt handler. Next section when it comes register function, I will explain the usage in more details.

####The new Hypercall
New hypercall number
{% highlight C %}
   POK_HYPERCALL_IRQ_REGISTER_VCPU 		   =  30,
   POK_HYPERCALL_IRQ_UNREGISTER_VCPU       =  31,
{% endhighlight %}

New case in pok_core_hypercall  
{% highlight C %}
pok_ret_t pok_core_hypercall (const pok_hypercall_id_t       hypercall_id,
                            const pok_hypercall_args_t*    args,
                            const pok_hypercall_info_t*    infos)
{
....
  /* register interrupt delivery to vcpu */
   case POK_HYPERCALL_IRQ_REGISTER_VCPU:
       return pok_bsp_irq_register_vcpu(args->arg1,(void(*)(uint8_t)) ((args->arg2 + infos->base_addr)));
       break;
   /* unregister interrupt delivery to vcpu */
   case POK_HYPERCALL_IRQ_UNREGISTER_VCPU:
       return pok_bsp_irq_unregister_vcpu(args->arg1);
       break;
....
}
{% endhighlight %}

The implementation of corresponding function
pok_bsp_irq_register_vcpu function in pok/kernel/arch/x86/x86-qemu-vmm/bsp.c  

{% highlight C %}
/*
 * Register irq in vCPU.
 * This irq must register in POK kernel first.
 * The parameter vector is the irq number.
 * The handle_irq is a common Entry from Guest OS.
 */
pok_ret_t pok_bsp_irq_register_vcpu(uint8_t vector,void (*handle_irq)(uint8_t))
{
  uint8_t i;
  struct vcpu *v;
  
  if(vector < 32)
    return POK_ERRNO_EINVAL;
  v = pok_partitions[POK_SCHED_CURRENT_PARTITION].vcpu;
  for (i=0; i<16; i++)
  {
    if(v->arch.irqdesc[j].vector == 0)
    {
      v->arch.irqdesc[j].vector=vector;
      v->arch.handler=(uint32_t) handle_irq;
      return POK_ERRNO_OK;
    }
  }
}
{% endhighlight %}

As we can see, this structure in vCPU is not correspond to certain IRQ in POK kernel. Once you need some to handling some interrupt in vCPU, you invoke this hypercall, then this function will find an empty irq_desc, then assign the irq as it passed in hypercall, and set the handler of Guest OS.

####Add the mask function in interrupt function.
As we did not differentiate the physical interrupt and virtual interrupt now, so we treat pit interrupt as other interrupt, mask it, and deliver it.  

Let's see the code of pit's interrupt handler.
{% highlight C %}
INTERRUPT_HANDLER(pit_interrupt)
{
   //uint8_t vector;
   //vector = 32;
   (void) frame;
   pok_pic_eoi (PIT_IRQ);
   do_IRQ(32);
   CLOCK_HANDLER;
}
{% endhighlight %}

So let's grab do_IRQ and check it out.
{% highlight C %}
#ifdef POK_NEEDS_X86_VMM

/*
 * Deal with the interrupt if the interrupt should be handler by guest
 */
void do_IRQ(uint8_t vector)
{
  do_IRQ_guest(vector);
}

/*
 * Decide the interrupt should be send to guest or not
 */
void do_IRQ_guest(uint8_t vector)
{
  uint8_t i,j;
  struct vcpu *v;
  for(i = 0 ; i < POK_CONFIG_NB_PARTITIONS ; i++)
  {
    v = pok_partitions[i].vcpu;
    for (j = 0 ; j< 16; j++)
    {
      if(v->arch.irqdesc[i].vector == vector)
      {
        v->arch.irqdesc[i].pending = TRUE;
	v->pending = TRUE;
	v->arch.irqdesc[i].count++;
      }
    }
  }
}

#endif /* POK_NEEDS_X86_VMM */
{% endhighlight %}

The do_IRQ is supposed to do some common treatment for interrupt, but I can't see any of them. and do_IRQ_guest will, as I said before, check the irq_desc array in vCPU, if there is a register of this interrupt, mask it, counter++.  

This is all of the jobs in POK kernel of interrupt delivery.  
There is three point in this implementation:  
1. The addition of vCPU structure, how we manage the interrupt.  
2. add register function in hypercall.  
3. add vCPU mask function in corresponding interrupt handler.  

However, for first point, there are still something remained to be discussed. Is the way we manage the interrupt register and mask improvable?
The approach now is simple enough, but also not effective enough in register, and mask function.
