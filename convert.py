#!/usr/bin/env python2

import os
rootdir = "./images/gallery/"
basetext1 = "  - url: /gallery/"
basetext2 = "\n    image_path: /gallery/"
basetext3 = "\n    alt: \n    title: \n"
gallery = ""

os.chdir(rootdir)

for  _,_,fns in os.walk("./"):
  for fn in fns:
    if "-l" not in fn:
      tmpfn = fn[:-4] + "-l.jpg"
      if not os.path.exists(tmpfn):
        os.system("convert -resize 400x400 " + fn + " " + tmpfn)
        print "convert file " + fn + " successfully"
        gallery = gallery + basetext1 + fn + basetext2 + tmpfn + basetext3
      else:
        print fn + " little image already exists"
        gallery = gallery + basetext1 + fn + basetext2 + tmpfn + basetext3
print gallery

