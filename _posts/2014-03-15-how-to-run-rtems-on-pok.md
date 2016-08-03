---
layout: single
title: "How to run RTEMS on POK"
modified:
categories: 
excerpt:
tags: []
image:
  feature:
  teaser: home.jpg
  thumb:
---
#####First: Build your POK example.
1. get pok source code from my <a href="https://github.com/HuaiYuSched/rtems_GSoC/tree/master/pok">github</a>.
2. change the directory to top of POK and export POK_PATH=$PWD.
3. run make configure.
4. cd to example and mkdir yourexample directory.
5. build a new example. If you got any question, find solution from pok-devel mail list or the <a href="http://download.tuxfamily.org/pok/snapshots/pok-userguide-current.pdf">document</a>. 

Here is the snapshot:
![]({{site.img_url}}/myexample.png)


#####Build RTEMS guest in POK
1. change directory to example/rtems-guest
2. make (will fail because undefined C_dispatch_isr)
3. build RTEMS. See next section.
4. copy the hello.exe sample to POK_PATH/example/rtems-guest/generated-code/cpu/part1/ (mv hello.exe part1.elf).
5. cd POK_PATH/examples/rtems-guest/generated-code/cpu/ and make all.
6. cd POK_PATH/examples/rtesm-guest/ and make run.


#####How to build RTEMS?
How to build RTEMS with --enable-paravirt and --enable-rtemsbsp=virtualpok?
 
1. get the source code from <a href="https://github.com/RTEMS/rtems.git">git</a>   
git clone https://github.com/RTEMS/rtems.git
 
2. get the patchs from my <a href="https://github.com/HuaiYuSched/rtems_GSoC">github</a>.(The patchs is written by Philipp Eppelt)  
<a href="https://github.com/HuaiYuSched/rtems_GSoC/blob/master/virtualpok-BSP.patch">virtualpok-BSP.patch</a>   
[rtems_paravirt_cpu_i386.patch](https://github.com/HuaiYuSched/rtems_GSoC/blob/master/rtems_paravirt_cpu_i386.patch)
 
3. patch the patchs.   
cd $RTEMS   
cat virtualpok-BSP.patch | patch -p1
cat rtema_paravirt_cpu_i386.patch | patch -p1
 
4. change the $RTEMS/c/src/lib/libbsp/i386/virtualpok/Makefile.am   
There are two kinds of  rename in linux, one is C version, the other is perl version. Check which version the rename is in you system.   
man rename, the C version will display "Linux Programmer's Manual RENAME(1)" while the Perl version will display "Perl Programmers Reference Guide RENAME(1)"   
If you are perl version, you can skip this step, otherwise, you have to change the Makefile.am
Change the statement "rename .lo .o `cat libpart.list`" to "cat libpart.list | rename 's/\.lo/\.o/g'"
 
5. cp the virtualizationlayercpu.h from $POK_PATH/example/rtems-guest/ to $RTEMS/c/src/lib/libbsp/i386/virtualpok/include. 

6. cp the libpart.a from $POK_PATH/examples/rtems-guest/generated-code/cpu/part1 to $RTEMS/c/src/lib/libbsp/i386/virtualpok/.

7. $RTEMS/bootstrap -p
 
8. change the include of virtualizationlayercpu.h in virtualpok/clock/ckinit.c from #include<rtems/score/virtualizationlayercpu.h> to #include<virtualizationlayercpu.h>
	
9. Build RTEMS.   
the configure line should looks like this.
--target=i386-rtems4.11 --enable-rtemsbsp=virtualpok --enable-paravirt
--disable-cxx --disable-networking --disable-posix
--enable-maintainter-mode --enable-tests --disable-multiprocessing
USE_COM1_AS_CONSOLE=1 BSP_PRESS_KEY_FOR_RESET=0   
when build the RTEMS, it's prossible to have some wrong occures due to the changes in RTEMS kernel, fix it by replace the file in [Phipse's Github](https://github.com/phipse/rtems)


#####After build the RTEMS on POK.
Here is the snapshot of result:  

![]({{site.img_url}}/RTEMSonPOK.png)
