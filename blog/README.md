# Hugo 博客（PaperMod）

与仓库根目录下的教程 Markdown 通过 `hugo.toml` 中的 `module.mounts` 关联，无需复制正文。

## 本地预览

1. 安装 [Hugo Extended](https://gohugo.io/installation/)（建议 **0.120+**，与 CI 使用的 **0.161.x** 接近可减少差异）。
2. 拉取主题（与 CI 相同）：

```bash
cd blog
rm -rf themes/PaperMod
git clone --depth 1 https://github.com/adityatelange/hugo-PaperMod.git themes/PaperMod
```

3. 启动：

```bash
hugo server -D
```

浏览器打开终端里提示的地址（一般为 `http://localhost:1313/`）。本地默认使用 `hugo.toml` 里的 `baseURL`，仅影响部分绝对链接；与线上不一致属正常现象。

## GitHub Pages

1. 在 GitHub 上把**本仓库**（含 `blog/` 与 `.github/workflows/`）推送到默认分支 `main` 或 `master`。
2. 仓库 **Settings → Pages**：**Build and deployment** 的 **Source** 选 **GitHub Actions**（不要选 Deploy from a branch）。
3. 首次推送后打开 **Actions** 查看 **Deploy Hugo site to Pages** 是否成功；站点地址为：

`https://<你的用户名小写>.github.io/<仓库名>/`

工作流会用 `hugo --baseURL` 自动按「当前仓库名」生成线上地址，**一般不必改 `hugo.toml` 里的 baseURL**（与 CI 一致即可，或保留作本地参考）。

## 新增一个系列（栏目）

1. 在 `blog/hugo.toml` 末尾增加一组 `[[module.mounts]]`，`source` 指向新系列 Markdown 所在目录（相对 `blog/`），`target` 为 `content/<栏目英文名>`。
2. 在 `blog/content/<栏目英文名>/` 下新建 `_index.md`（可参考现有 `intro` 等目录）。
3. 在 `hugo.toml` 的 `[menu.main]` 里增加一项，指向 `/<栏目英文名>/`。
4. 提交并推送，等待 Actions 部署。

## 在已有系列里加文章

把新的 `.md` 放进对应教程仓库里被 mount 的目录（例如 `音视频入门教程/publish/`），推送后重新构建即可。

## 仅用命令行新建草稿（可选）

```bash
cd blog
hugo new intro/我的新文章.md
```

若该系列内容由 mount 提供，更常见做法是**在源目录加 md**，而不是在 `blog/content/intro/` 下再建一层，以免与 mount 策略混淆；以你当前「源文在外层目录」的模型为准。
