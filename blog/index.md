---
layout: archive
title:
excerpt: ""
image:
  feature:
id: home
---
<div class="page-feature-header overlay">
  <div class="page-image" style="margin-top: 0 !important;"><!-- remove inline CSS for production -->
    <img src="/images/sea.jpg" class="page-feature-image" alt="Page Titles with Feature Image">
  </div>
  <div class="page-title">
    <h1><span>Youren Shen</span></h1>
    <h2><span>Live in Beijing China, now.</span></h2>
    <h3 style="text-transform: inherit"><span>黄金燃桂尽，壮志逐年衰。</span></h3>
  </div>
  {% for post in site.posts %}
	{% include post-grid.html %}
{% endfor %}
</div>
