---
layout: single
title: "The pok_sched function"
modified:
categories: 
excerpt:
tags: []
image:
  feature:
  teaser: home.jpg
  thumb:
---
The startup of POK kernel, especially for kernel space to user space, is so obscure that confused me continuously untill last week I spent some day to following the instruction of POK line by line in GDB.

The purpose of this behavior, that I analysis the pok_sched function in details, is try to find out the appropriate time to insert the function of interrupt handling of guest OS. This time should be when the partition is switched. And in this time, we should check the interrupt for new partition.  
####background
When the POK kernel starting, the POK kernel will create a context of every partition main thread.
pok_partition_init->pok_partition_setup_main_thread->pok_partition_thread_create->pok_space_context_create.
This context will be used when pok_sched first run.


####Where is the pok_sched is invoked?
Of course pit_interrupt(timer interrupt handler).

####What the pok_sched function do?
In a word, the pok_sched elect next partition and it's thread. then switch to it. 
What important is how it switchs:

{% highlight C %}
void pok_sched_context_switch (const uint32_t elected_id)
{
   uint32_t *current_sp;
   uint32_t new_sp;

   if (POK_SCHED_CURRENT_THREAD == elected_id)
   {
      return;
   }

   current_sp = &POK_CURRENT_THREAD.sp;
   new_sp = pok_threads[elected_id].sp;
/*
    *  FIXME : current debug session about exceptions-handled
   printf("switch from thread %d, sp=0x%x\n",POK_SCHED_CURRENT_THREAD, current_sp);
   printf("switch to thread %d, sp=0x%x\n",elected_id, new_sp);
   */
   pok_space_switch(POK_CURRENT_THREAD.partition,
		    pok_threads[elected_id].partition);

   current_thread = elected_id;

   pok_context_switch(current_sp, new_sp);
}
{% endhighlight %}

As we can see, the pok_space_switch will change the GDT according to the partition id, that is, the function of divide change.
Then we used the current thread's stack point, and next thread's stack point as parameters to pass to pok_context_switch.
{% highlight C %}
void			pok_context_switch (uint32_t* old_sp,
                                uint32_t new_sp);
asm (".global pok_context_switch	\n"
     "pok_context_switch:		\n"
     "pushf				\n"
     "pushl %cs				\n"
     "pushl $1f				\n"
     "pusha				\n"
     "movl 48(%esp), %ebx		\n" /* 48(%esp) : &old_sp, 52(%esp) : new_sp */
     "movl %esp, (%ebx)			\n"
     "movl 52(%esp), %esp		\n"
     "popa				\n"
     "iret				\n"
     "1:				\n"
     "ret"
     ); 
{% endhighlight %}
it's essential to comprehend this segment of code that understanding the switch of stack point. Firstly, we push flag register in stack, and then CS, and finally the return address of pok_context_switch. this three push instructions corresponding to the iret instruction below. It seems dispensable here, you push the next line of iret, and then using iret to return next line. We will see it usefulness in next section.

After this ,we push all register, switch stack points, and then pop all register for next thread. It's normally task switch routine and immentionable.

####The first time of the pit interrupt running.

The thread zero(the startup thread ) will go to forever loop after initialization. and first time the pit_interrupt was invoke, what should be next thread?

The first time, the context was fake and initialize in pok_space_context_create.
{% highlight C %}
uint32_t	pok_space_context_create (uint8_t  partition_id,
                                   uint32_t entry_rel,
                                   uint32_t stack_rel,
                                   uint32_t arg1,
                                   uint32_t arg2)
{
  ....
   sp->ctx.__esp  = (uint32_t)(&sp->ctx.eip); /* for pusha */
   sp->ctx.eip    = (uint32_t)pok_dispatch_space;
   sp->ctx.cs     = GDT_CORE_CODE_SEGMENT << 3;
   sp->ctx.eflags = 1 << 9;

   sp->arg1          = arg1;
   sp->arg2          = arg2;
   sp->kernel_sp     = (uint32_t)sp;
   sp->user_sp       = stack_rel;
   sp->user_pc       = entry_rel;
   sp->partition_id  = partition_id;
....
}
{% endhighlight %}

As we can see, the eip of this context was set as pok_dispatch_space. 
So first time, the pit_interrupt will invoke this function.

After all of this analysis, I find the pok_sched is the function where switch the partitions, however, I'm hesitating because of the fat of pit_interrupt function now. should I put more things in this interrupt?
