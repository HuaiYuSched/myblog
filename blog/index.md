---
layout: archive
title: Youren's Blog
excerpt: "Lives at Beijing China. "
header:
  overlay_image: sea.jpg

---
{% include base_path %}

<h3 class="archive__subtitle">{{ site.data.ui-text[site.locale].recent_posts | default: "Recent Posts" }}</h3>

{% for post in site.posts %}
  {% include post-grid.html %}
  {% endfor %}


