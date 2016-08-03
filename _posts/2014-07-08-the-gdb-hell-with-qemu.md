---
layout: single
title: "The GDB hell with qemu"
modified:
categories: 
excerpt:
tags: []
image:
  feature:
  teaser: home.jpg
  thumb:
---


Last week the rtems example can't work normally anymore, so I try to find out the reason of this bug. 


Firstly I tried to follow the POK Developper Guide,  
 * invoke make run-gdb   
 * gdb pok.elf   
In the gdb I follow the guide
 * target remote:1234 
Then I trying the break in pok_boot. but every time I failed. The GDB pass the breakpoint and did not stop. I was confused about this, I consider that the POK.elf did not load successfully. So I restart the GDB, and step every single instructions by si, trying to find out the reason of the bug. however, the memory is all zero. and after some zero instruction, the program crashed.   
![]({{site.img_url}}/All\ zero\ memory.jpg)  
Following the Guide is not practicable, so I trying to find other way in myself.  

I hypothesize that the reason of all-zero-memory is that the qemu did not loaded the pok.elf yet. However, because of the bug of GDB, I can't stop on pok_boot. then I google the error. I guess maybe the POK.elf is misloaded so the memory is wrong. But this attempt of solving problem is fruitless. 

Then I Google it and find out that this is a bug of GDB[1], that the GDB will not stop on soft break point first time. So I set hardware-assist-breakpoint on pok_boot. this time worked.

However, I add-symbol-file part1/part.elf and trying to set it on boot_card in RTEMS. But this time the program crash directly.

So I step it and in the pok_arch_preempt_enable when the sti(interrupt enable instruction.) invoke, the problem crash. At first I check the POK kernel and make sure that the eflags allow the sti.

Secondly, I try to set hardware-assist-break point in boot_card and start. but the problem still crash directly. I consider that the program crash when the POK is trying to load it to memory. So I check the model.addl and the file size of pok.elf and partition.bin. Finally the reason is revealed, the space of model is so less that it can't contain the partition.

This bug impede me more than three days because of the obscure debug workflow. So I record it in this post.  


[1]. https://bugs.launchpad.net/ubuntu/+source/qemu-kvm/+bug/901944
