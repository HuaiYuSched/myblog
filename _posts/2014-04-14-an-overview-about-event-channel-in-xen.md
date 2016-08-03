---
layout: single
title: "An overview about Event Channel in XEN"
modified:
categories: 
excerpt:
tags: []
image:
  feature:
  teaser: home.jpg
  thumb:
---

####How to use event channel in XEN

There are three sort of events in XEN: interdomain events, physical IRQ, and virtual IRQs(VIRQ).The event will be enqueued even when the domain is not executing, and then deliver when it is. But the traps ,for example the divided zero error, should be deliver directly.  

1. Requesting Events.
The first step of using an event in XEN is requesting an event for the domin. The meaning of "requesting" is to bond an event channel to an event source. So the step could be divided to be two stages:
   1. Binding the channel to an event source.
   2. Configuring a handler for the event.   
For example:
Binding the timer virtual interrupt:
{% highlight C %}
evtchn_bind_virq_t op;
op.virq = VIRQ_TIMER;
op.vcpu = 0;
if(HYPERVISORevent_channel_op(EVTCHNOP_bind_virq, &op) != 0)
{
  /*handle the error*/
}
{% endhighlight %}

2. Set callback function.

{% highlight C %}

  HYPERVISOR_set_callbacks(
    FLAT_KERNEL_CS, (unsigned long)hypervisor_callback,
    FLAT_KERNEL_CS, (unsigned long)failsafe_callback);
{% endhighlight %}

####Introduced the workflow of event channel in short. 
1. When the event occurs, the corresponding bit in domain.share_info->evtchn_pending will be set, then the vcpu_mark_events_pending will be invoked, which will set the bit of vcpu.vcpu_info->evtchn_upcall_pending.
2. Every time when return from interrupts, the evtchn_upcall_pending will be check, when this bit isn't 0, the event handler workflow will be invoked.
3. The event handler workflow usually will invoke the hypervisor_callback.

####What we should do?
As we can see now, we have to finish the following part in notify module:  
1. Build a structure to store the context of interrupt.  
2. Build a structure to mark that there is an event pending.  
3. When the partition(RTEMS) resume, check the value of the bit.  
4. Design a callback function mechanism. Including the operation of register an event and callback function. The register of events should bind the corresponding partitions.  
5. In the callback function, we should invoke the normal interrupt handler in RTEMS, let the RTEMS deal with this interrupt.  

####Addition
The event channel is more complex then I expect before, So I could only give a overview about it. The purpose of this post is not trying to introduce every deatail in XEN, and it's not necessary to do so.   
We just need to find the basic solution of the XEN about the interrupt handler. Adopt it's basic idea to POK and RTEMS.

If I got anything wrong or any problem, Please connect me via <shenyouren@gmail.com>

####Reference:
[1]. Chisnall, David. The definitive guide to the xen hypervisor. Pearson Education, 2007.   
