---
title: "{{ replace .File.ContentBaseName "-" " " | title }}"
date: {{ .Date.Format "2006-01-02T15:04:05Z07:00" }}
draft: false
# 将 myseries 改为你新建的栏目目录名；或放在已有系列目录下用 hugo new myseries/篇名.md
series: []
---
