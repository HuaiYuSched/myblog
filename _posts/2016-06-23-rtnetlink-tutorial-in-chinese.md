---
layout: single
title: "RTnetlink Tutorial in Chinese"
modified:
categories:
excerpt:
tags: [Network]
image:
  feature:
  teaser:
  thumb:
date: 2016-06-23T01:40:26+08:00
---
rtnetlink是基于netlink机制的一个内核和协议栈相关操作的机制。其允许用户程序对内核的路由表进行读写。是Linux 2.2之后的一个新的功能。这个功能非常重要，在很多基础的工具中的使用也非常广泛。但是很少资料直接对rtnetlink的具体使用进行讲解，中文的资料只有一些对[Manual]的翻译和补充，Linux journal有非常详细的一篇框架文章，但是对具体过程解释不详细。另一方面，由于现实的应用中，对路由表等的处理较为复杂，没有比较简单直接的例子。并且其[Manual]中说到这个是Linux IPv4的路由 socket，但是其支持Ipv6，应该是[Manual]太久没更新的缘故。   
因此，这篇文章并不对rtnetlink的数据结构或[Manual]进行详细的解释，而是解释其使用方式，并且举一个具体的使用样例。对一些操作和数据结构的构成有疑惑，可以直接看[Manual]。   

## Netlink
首先，解释一下rtnetlink中的netlink的使用。netlink是基于Socket的一个内核和用户空间的交换机制，因此其API接口看起来和Socket是一致的。  

```c   
int socket(int domain, int type, int protocol);   
```

具体的在netlink的应用中：  

```c  
fd = socket(AF_NETLINK, SOCK_RAW, NETLINK_ROUTE);   
```  

而后用Send/sendto/sendmsg函数将rtnetlink的数据发给内核即可。   
```c
send(socket_fd, msg, msg_len,0)      
```    


而在接收时，亦可使用标准的recv函数。  
对于netlink数据包的构造和解构，通过zmap中的两个函数来解释。  
这两个从zmap中拿来的函数，其将netlink的内容封装的很好，我们之后就可通过这两个函数调用来说明问题。  

```c
read_nl_sock(int sock, char *buf, int buf_len)
{
        int msg_len = 0;
        char *pbuf = buf;
        do {
                int len = recv(sock, pbuf, buf_len - msg_len, 0);
                if (len <= 0) {
                        log_debug("get-gw", "recv failed: %s", strerror(errno));
                        return -1;
                }
                struct nlmsghdr *nlhdr = (struct nlmsghdr *)pbuf;
                if (NLMSG_OK(nlhdr, ((unsigned int)len)) == 0 ||
                                                nlhdr->nlmsg_type == NLMSG_ERROR) {
                        log_debug("get-gw", "recv failed: %s", strerror(errno));
                        return -1;
                }
                if (nlhdr->nlmsg_type == NLMSG_DONE) {
                        break;
                } else {
                        msg_len += len; pbuf += len; }
                if ((nlhdr->nlmsg_flags & NLM_F_MULTI) == 0) {
                        break;
                }
        } while (1);
        return msg_len;
}

int send_nl_req(uint16_t msg_type, uint32_t seq,
                                void *payload, uint32_t payload_len)
{
        int sock = socket(PF_NETLINK, SOCK_DGRAM, NETLINK_ROUTE);
        if (sock < 0) {
                log_error("get-gw", "unable to get socket: %s", strerror(errno));
                return -1;
        }
        if (NLMSG_SPACE(payload_len) < payload_len) {
                close(sock);
                // Integer overflow
                return -1;
        }
        struct nlmsghdr *nlmsg;
        nlmsg = xmalloc(NLMSG_SPACE(payload_len));

        memset(nlmsg, 0, NLMSG_SPACE(payload_len));
        memcpy(NLMSG_DATA(nlmsg), payload, payload_len);
        nlmsg->nlmsg_type = msg_type;
        nlmsg->nlmsg_len = NLMSG_LENGTH(payload_len);
        nlmsg->nlmsg_flags = NLM_F_DUMP | NLM_F_REQUEST;
        nlmsg->nlmsg_seq = seq;
        nlmsg->nlmsg_pid = getpid();

        if (send(sock, nlmsg, nlmsg->nlmsg_len, 0) < 0) {
                log_error("get-gw", "failure sending: %s", strerror(errno));
                return -1;
        }
        free(nlmsg);
        return sock;
}
```


其中，send_nl_req中，第一个参数是rtnetlink的请求类型，第二个参数是包的序号，例子中可以为0，第三个参数为发送的包的内容，最后为包的长度。
根据给出的四个参数，就可以构造出合适的发送包nlmsg.   
read_nl_req 也是类似。   
更详细的信息，请参看这篇[Blog][2]   

## rtnetlink数据流
为了理解rtnetlink中的数据结构之间的关联，首先要了解其数据流。  
自然，基于socket机制的通信过程是发送请求以后接收回复，接下来结合[Manual]描述更加具体的通信中数据流的解释。  
首先，rtnetlink的消息类型有可以分为以下几种类型：  

1.LINK型   
该类型的消息主要是对网卡的L2地址进行操作，即网络设备的mac地址，消息类型包括RTM_NEWLINK, RTM_DELLINK, RTM_GETLINK。Link型的消息在通信过程中涉及到的数据结构有ifinfomsg结构以及多个rtattr结构。   

2.ADDR型   
该类型的消息主要是对网卡的IP地址进行操作。消息类型包括RTM_NEWADDR, RTM_DELADDR, RTM_GETADDR。Addr型的消息在通信过程中涉及到的数据结构有一个ifaddrmsg结构以及多个rtaddr结构。   
 
3.ROUTE型  
该类型主要对网卡的路由表进行操作。消息类型类似包括RTM_NEWROUTE, RTM_DELROUTE, RTM_GETROUTE。Route型的消息包含一个rtmsg结构，其后跟数目可选的rtattr结构。  
4.NEIGH型   
5.RULE型  
6.QDISC型  
其中，第4、5和6种类型的消息，可以参看[Manual]或者这篇[Blog][1].   

以Link型的消息为例，解释下机器的网卡硬件地址，那么其通信过程由以下几步构成：  
1.人为构造一个ifinfomsg作为你的请求（req）结构  
2.将Req通过send_nl_req 接口发送出去，通过 read_nl_sock读取回复   
3.解构出回复的消息包。  

消息包的构造如下图所示：  

![The structure of rtnetlink request]({{site.img_url}}/rtnetlinkmsg.jpg)  

每次接收到的回复中可能会包括若干个netlink message，而每个netlink message包括一个特定的消息头以及若干的rt_attr结构。其中，特定的消息头中一般存有设备或地址的属性，而rt_attr结构存储具体的数据如硬件地址或ip地址。   
具体的，linux/rtnetlink.h有一系列的宏负责对这些结构体进行操作。可以参看[Linux journal][3]中对其进行的解释。  

## rtnetlink的使用
接下来我将以获得网关IP为例，解释rtnetlink具体的使用。   

```c
_get_default_gw(char *addr, char *iface, const int family)
{
  struct rtmsg req;
  unsigned int nl_len;
  char buf[8192];
  struct nlmsghdr *nlhdr;

  if (!addr || !iface) {
    return -1;
  }

  // Send RTM_GETROUTE request
  memset(&req, 0, sizeof(req));
  req.rtm_family = family;
  int sock = send_nl_req(RTM_GETROUTE, 0, &req, sizeof(req));

  // Read responses
  nl_len = read_nl_sock(sock, buf, sizeof(buf));
  if (nl_len <= 0) {
    return -1;
  }

  // Parse responses
  nlhdr = (struct nlmsghdr *)buf;
  while (NLMSG_OK(nlhdr, nl_len)) {
    struct rtattr *rt_attr;
    struct rtmsg *rt_msg;
    int rt_len;
    int has_gw = 0;

    rt_msg = (struct rtmsg *) NLMSG_DATA(nlhdr);

    if ((rt_msg->rtm_family != family) || (rt_msg->rtm_table != RT_TABLE_MAIN)) {
      return -1;
    }

    rt_attr = (struct rtattr *) RTM_RTA(rt_msg);
    rt_len = RTM_PAYLOAD(nlhdr);
    while (RTA_OK(rt_attr, rt_len)) {
      switch (rt_attr->rta_type) {
      case RTA_OIF:
        if_indextoname(*(int *) RTA_DATA(rt_attr), iface);
        break;
      case RTA_GATEWAY:
        //gw->s_addr = *(unsigned int *) RTA_DATA(rt_attr);
        inet_ntop(family, RTA_DATA(rt_attr), addr,64);
        has_gw = 1;
        break;
      }
      rt_attr = RTA_NEXT(rt_attr, rt_len);
    }

    if (has_gw) {
      return 0;
    }
    nlhdr = NLMSG_NEXT(nlhdr, nl_len);
  }
  return -1;
}
```

\_get_default_gw 函数获得当前的默认网关，第一个参数是保存网关地址的buf，第二个参数是网络接口的名称，第三个参数是协议族（AF_INET/AF_INET6）。按照三步走：   

### 构造请求包   
获得网关是需要从路由表中获取的，因此这个例子中，我们使用getROUTE 类型的消息。而在请求包中将对应的地址协议写上，就意味着选择了对应的协议。  

### 发送并接收包   
使用之前封装好的API，将消息发送给内核。  

### 解构消息   
    a.将buf赋值给nlhdr，并使用NLMSG_OK宏判断netlink消息的合法性（是否还有未处理的消息）  
    b.将nlmsg消息解构。通过NLMSG_DATA宏，获得rtnetlink的消息，并判断这个消息的属性是否是正确的。我的判断是第33行看协议族是否一致，是否是一个路由表。  
    c.如果这个renetlink的消息是可靠的，此时可以通过rt_msg的属性对rt_attr中的数据进行获取并解读。此处当其是一个路由消息时，我将它转换为可读的ip地址填充到参数中。  
    d.迭代RT_attr，迭代netlink message。  
    

[1]: http://blog.csdn.net/romainxie/article/details/8300443      
[2]: http://www.cnblogs.com/hoys/archive/2011/04/09/2010788.html "linux内核与用户空间通信之netlink使用方法"    
[3]: http://www.linuxjournal.com/article/8498 "Manipulating the Networking Environment Using RTNETLINK"    
[Manual]: http://man7.org/linux/man-pages/man7/rtnetlink.7.html "RTNETLINK(7)"    
