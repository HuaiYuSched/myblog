---
layout: single
title: "The concepts of virtual CPU"
modified:
categories: 
excerpt:
tags: []
image:
  feature:
  teaser: home.jpg
  thumb:
---

There are two concepts when it comes to virtual CPU. In some situations, the virtual CPU means what we should do with CPU in virtualzation to make the guest OS perform normally. On the others the virtual CPU is a structure in Hypervisor to manage the resources. That is say just a fake CPU for guest OS. 

####Virtual CPU.

|CPU          | The solution |
|------------ | ------------------------------------------- |
|Protection   | Guest OS must run at a lower privilege level than Xen. |
|Exceptions   | Guest OS must register a descriptor table for exception handlers with Xen. Aside from page faults, the handlers remain the same |
|System Calls | Guest OS may install a ‘fast’ handler for system calls, allowing direct calls from an application into its guest OS and avoiding indirecting through Xen on every call. |
|Interrupts   | Hardware interrupts are replaced with a lightweight event system. |
|Time         | Each guest OS has a timer interface and is aware of both ‘real’ and ‘virtual’ time. |

**<center>Table: The paravirtualization x86 interface of CPU[1].</center>**

> This table is reference from [1]. As it shows, we need to deal with the issues upon when we try to virtualiza the CPU.    

####vCPU 
The vCPU structure is a descriptor to describe the virtual CPU in hypervisor. The introduce of vCPU is part of like the process in traditional OS. Essentially, the vCPU is just a structure describe the resources in VMM.   
The component of a vCPU should contain:  

* The identifier of vCPU: to identify some attributions of vCPU, for instance, the id of a vCPU, the belonging of a vCPU.   
* The virtual register information. The virtual CPU information is about the fake register, like cpu_usr_regs structure I described in a early blog. However , if the CPU support the hardware-assist virtualization like intel VT-x, this information will be contain in Virtual-Machine Control Structure(VMCS). But it‘s not we concerned about.  
* The state information of vCPU: in some extent, this similar with the process state, to identify the state of the vCPU(sleep, running). This part is used by schedule.  
* Some other information. The other information is about optimization for VMM and extra information for vCPU.   

So as we can see, the vCPU is just a control block for VMM.

As for now I can see , there are two benefits from vCPU. First, the vCPU may support the SMP for RTEMS in the future( however, I don't know if POK not support SMP, what can take for us from this advantage.). Seccond, the interrupt can inject into vCPU, but not the partitions.

If there is anything not clear, please contact me <shenyouren@gmail.com>
####Reference
[1]. Barham, Paul, et al. "Xen and the art of virtualization." ACM SIGOPS Operating Systems Review 37.5 (2003): 164-177.
