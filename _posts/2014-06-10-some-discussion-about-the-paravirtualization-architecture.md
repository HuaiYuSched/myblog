---
layout: single
title: "Some discussion about the paravirtualization architecture"
modified:
categories: 
excerpt:
tags: []
image:
  feature:
  teaser: home.jpg
  thumb:
---
Some additional discussion.
####The interrupt architecture of virtual machine
![The interrupt architecture of virtual machine]({{site.img_url}}/The\ interrupt\ architecture\ of\ virtual\ machine.png)  

As we can see from the picture, these physical device interrupt will be tackle by VMM first, then be transform to be virtual interrupt then notify to vCPU. And also the VMM could generate the virtual interrupt and transfer to vCPU.

####The models of VMM.
There are four part of a VMM, maybe a little different with our works. P means Processor, it is responsible for the virtual CPU(interrupt, syscall, etc.). M means Memory, it is about memory virtualization management. DM is abbreviation of device model, it custody the I/O virtualization. The last one, DR is the abbreviation of device driver. 
#####Hypervisor model.
![Hypervisor model]({{site.img_url}}/Hypervisor\ Model.png)  
In the Hypervisor model, the VMM is more like a complete OS with virtualization support. All the jobs is doing in VMM.   
If we use this model, obviously the DR will be re-implement in POK, that's a huge job.  
#####Host model.
![Host model]({{site.img_url}}/Host\ model.png)  
In the Host model, the host OS will manage the physical resources. The VMM is just supply the function of virtualization.
#####Hybrid model.
![Hybrid model]({{site.img_url}}/Hybrid model.png)   
In the hybrid model, the Hypervisor will manage every physical resources, but the I/O will be handle by Guest OS.(like dom 0 in XEN). 

I prefer the Hybrid model, and I hope we can used the device driver in RTEMS. The first picture about interrupt is about the hybrid model, I think.   
So, `what your opinion?`
