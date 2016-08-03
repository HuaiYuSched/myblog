---
layout: single
title: "The design of vCPU in POK"
modified:
categories: 
excerpt:
tags: []
image:
  feature:
  teaser: home.jpg
  thumb:
---

If introduced vCPU into POK, then the architecture of paravirtualization will change. we add a VMM layer in to paravirtualization like Philipp's illustration. (see below);  
I add a lot of explanation as comments, so please read the comments to get necessary infomation.  
This is just a draft, so the name of functions and values is only for illustrations their roles.
####The structure of vCPU.
{% highlight C %}
struct vcpu
{
	/* 
	 * The number of vcpu. To use this number to identify the vcpus, we 
	 * should implement a system to generate the unique number in system and 
	 * recycle them. 
	 */  
	vcpu_id id;		
	/* 
	 * This is a list of vcpu, to organize vcpu in logic.
	 */  
	struct vcpu *prev,*next;
	/* 
	 * This id support us to bind the cpu with partitions.
	 */  
	partition_id partition;
	/* 
	 * The runstate indicate the state of vcpu, suggest to have running, 
	 * ready, 
	 * suspending.
	 */  
	vcpu_runstate_info runstate;
	/* this is about sched_info, as for now, I can't figure out the 
	 * algorithm of schedule, so this part is omit.
	 */
	vcpu_sched_info sched_info;
	/* 
	 * This struct contains some arch-dependent operations and attributes.
	 */
	vcpu_arch arch; 
}
{% endhighlight %}

{% highlight C %}
struct vcpu_arch
{
	/* 
	 * some arch-dependent attributes;
	 */
	vcpu_guest_context cxt;
	/* 
	 * some arch-dependent operations;
	 */
	void (*ctxt_switch_from) (struct *vcpu);
	void (*ctxt_switch_to) (struct * vcpu);
	void (*schedule_tail) (strcut * vcpu);
	/*
	 * interrupt information.
	 */
	interrupt_struct pending_interrupt;
}
{% endhighlight %}

####The initialization of vCPU.
The function of vCPU initialize is alloc_vcpu().  
{% highlight C %}
struct vcpu *alloc_vcpu( partition_id pid, vcpu_id vid );
{% endhighlight %}
#####When to create a vCPU.
When a partition setup, the vCPU should be created and bind with current partition. so we should insert alloc_vcpu in pok_partition_init.
#####How to create a vCPU.
Essentially the initialization of vCPU is a process of filling the structure.
{% highlight C %}
struct vcpu *alloc_vcpu( partition_id pid, vcpu_id vid )
{
	struct vcpu *v;
	/* 
	 * alloc the space of vcpu structure;;
	 */
	v = alloc_vcpu_struct();

	/* 
	 * set the vcpu_id; 
	 */
	v->id = vid;
	/* 
	 * set the partition id, bind the partition with vcpu.
	 */
	v->partition = pid;
	/* 
	 * initialize the schedule information, mostly about time.
	 */
	if (sched_init()==0)
	{
		destroy_vcpu(v);
		return;
	}
	/*
	 * set run states;
	 */
	v->runningstate = running;
	/* 
	 * This function will bind the arch-dependent operation will 
	 *corresponding function, and fill the arch-dependent attributes;
	 */
	if (vcpu_initialize()==0)
	{
		destroy_vcpu(v);
		return;
	}

}
{% endhighlight %}
The function should be implement has been list upon.
#####Problem remains.
How to get a unique vcpu_id?  
Is there already have a system to generate and organize identified number in POK?   

####The operations of vCPU.
The program is constructed by algorithm and metadata. If the vCPU structure, in this situation, is metadata, then the what's the algorithm? For example, the schedule certainly is one of the algorithm. On the other hand, as we concerned, if we got virtual CPU, the interrupt can be bond with vCPU, but not partition. So the inject of interrupt will be other algorithm of vCPU. 

#####The register of interrupt(bind vCPU with interrupt)
This part is not clear before we adapt the mechanism of interrupt and notify system.

#####The injection of interrupt to vCPU.
This part is not clear before we adapt the mechanism of interrupt and notify system.

#####Schedule.
Here is two issues remain to be discussed.   
Of course, we can design some interface of schedule that is related to vCPU now.  

1. ctxt_switch_from(p);	//save the context of current vCPU context.  
2. ctxt_switch_to(n);	//load the context of next vCPU context.  
3. schedule_tail(n);	//switch to next vCPU.   

######The architecture of schedule.
The XEN consider vCPU as processes in traditional OS, so XEN schedule vCPU to organize whole system. In the KVM ( Kernel-based Virtual Machine ), a virtual machine is a system thread, so the schedule is Linux kernel's schedule.   
As for POK, the schedule exist already, the schedule object is partitions. And I think it's not easy/rational to cancel or replace it. So here we have two solutions:   

1. Replace the partitions with vCPU in schedule algorithm.  
2. Build a schedule for vCPU in partition layer. i.e., there will be two schedule in POK.  

I recommend to second solution, for keep SMP in mind as Philipp told me.


######The algorithm of schedule.

Once we determine using the second architecture of schedule, we should decide what algorithm to be used.

####More operations.

By macro `current`, get the current vCPU's information.  
Set part of information of current vCPU.

Any operations more occurs to you, please tell me. <shenyouren@gmail.com>

####Additional information.
By introduce the vCPU into POK, we introduce a VMM layer into POK.
The architecture will become below:   
Here is Philipp's illustration:  
![Philipp's illustration]({{site.img_url}}/Philipp\'s\ design.jpg)
