---
layout: single
title: "The brief design and outline"
modified:
categories: 
excerpt:
tags: []
image:
  feature:
  teaser: home.jpg
  thumb:
---
As far as I discussed with Philipp for now, We have found two parts to do for this project.
Here is the architecture of our design:   
![The architecture of paravirtualization]({{site.img_url}}/The\ architecture\ of\ paravirtualization.png)

Here is Philipp's illustration:  
![Philipp's illustration]({{site.img_url}}/Philipp\'s\ design.jpg)

As we can see from the picture, the RTEMS invoke the hypercall by Paravirtualization Layer to communicate with hypervisor, and also the hypervisor will notify the RTEMS through the event channel(we using the concept in XEN temporarily, however, I think we will using the mechanism supplied by POK finally.)  
Also the RTEMS will be benefit from this clear and separate design in the future, since it's easy to reuse the paravirtualization layer to transplant the RTESM on other hypervisor. 


####Why hypercall? 
As a native operating system, the RTEMS and all user software executes at privilege level 0 on x86.[1]
Now, as a guest OS, the RTEMS running in privilege level 3(as default) which is not allowed to do everything. So we have to have some mechanism to resolve this problem.

As we can see, this is not a new problem. In the traditional OS, when the application in privilege level 3 wants to do some thing by hardware, like printing something in screen, or get the keyboard inputting, it will invoke the syscall, tell the OS what's to do, and the OS check the security of the operation, then do it for applications.

Being familiar with syscall, we now also want to do some privilege operation in a high privilege level, typically in level 3. So we could design some thing like syscall named as hypercall as the solution of this problem.

####How to handle the interrupts?

The correct way to handle a interrupt in most native operating system is installing a interrupt handler and when the interrupt occurs, jump to the entry of the interrupt handler.   
However, the paravirtualization hypervisor did not doing in this way. The interrupts has been divied into two types, one is the local interrupt, which is important and should be handle by POK, such as clock interrupt and other CPU exception., the other is guest interrupt. We using the hypercall to bind a event port when the guest OS set up. When the guest interrupt happens, we intercepts them rather than passing them directly through to RTEMS.This design allows the POK(also other hypervisor) remain the control of the hardware, scheduling servicing.   
However, like we said before, the RTEMS should be allowed to regiser interrupt handlers with POK by paravirtualization layer. And Interrupt occurs when the corresponding RTEMS is waitting to execute will be store in a package, then deliver to RTEMS when it is activated.   
When the RTEMS is activated, it should notice the interrupt delivered by event channel, and handle it with there own interrupt handler.

####How Xen handle a physical interrupt.
See it in my next weekend post.

####Clock system in paravirtualization.
Need to be discuss.

####Summary
* what should we implement paravirtualization layer?(in paravirtualization layer)
As far as concerned now, the to-dos in paravirtualization layer includes:
   1. Implement some kind of fake register, and corresponding hypercall with the sensitive instructions.[3]
   2. Implement the register interrupt operation in paravirtualization layer.
   3. Implement a callback function in RTEMS, which will be invoke when a interrupt is delivered. (Analogy with signal in UNIX). In this function, we will jump to the entry of the ture interrupt handler.
* what should we implement to dispatch the interrupts?(in POK kernel)
   1. adapt the meta_handler to workable with the register operation. which includes to add some flags to make the interrupt attribution and the corresponding partition.
   2. using the event channel to delivery interrupts.

####Brief Outline from now.

April 07 -- April 14
Reading the  code of the event channel in XEN and the workflow about interrupt delivery.
Write a post about it in weekend.

April 14 -- April 22
Reading the code of the communication mechanism of POK and design the detail of interrupt delivery by this communication mechanism.   
I will write a post about it in weekend.

April 22 -- May 19,2014(Design Period)
Giving more details about functions should be implement by the hypercall in paravirtualization layer.   
 
May 20 -- June 27,2014(code period)
In this period, I will accomplish the first and second step in paravirtualization layer and first step in POK kernel.   

I will post a blog about what I have do and submit the patch at the end of this period.
 
June 28 - July 11 2014 (code and test period)
During this period, I will finished all the cod jobs remain, and test some sample like divide zero error exception. Then trying to running more samples of RTEMS on POK.
 
July  12 - August 25 2014 (name)
Finish all missing documentation.
Write the wiki page.
Write a user manual to introduce how to use the API proived by paravirtualization layer and how to transplant the virtualization layer on another kind of operating system.

If you got any problem or I have any misunderstanding, please contact me by email <shenyouren@gmail.com>

####Reference:
[1]. <https://rtems.org/onlinedocs/doc-current/share/rtems/html/cpu_supplement/Intel_002fAMD-x86-Specific-Information-Vectoring-of-Interrupt-Handler.html>.   
[2]. Chisnall, David. The definitive guide to the xen hypervisor. Pearson Education, 2007.   
[3]. <https://docs.google.com/document/d/10ehcM1f2eKNwcNgv5stphGtsVAnYc_K7KLhxmjvE1k8/edit>.
