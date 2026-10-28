# Tibo 新帖邮件提醒（免费云端版）

监控 https://x.com/thsottiaux ，使用 GitHub Actions 标准 Linux runner，每 15 分钟检查，Gmail SMTP 给自己发邮件。不使用付费 X API，无第三方 Python 依赖。

## 部署

1. 在自己的 GitHub 账号创建公开仓库 `tibo-mail-monitor`。公开内容包含代码、帖子文本和运行状态，邮箱和授权码只放 Secrets。不要将私人内容写进仓库。
2. 将本目录全部文件上传，保留 `.github/workflows/monitor.yml` 路径。`monitor.py` 必须位于仓库根目录。
3. Gmail 开启两步验证，然后在 https://myaccount.google.com/apppasswords 创建应用专用密码。如果账号没有此选项，本方案的 Gmail 发送环节不能直接使用，需要更换支持 SMTP 的邮箱。
4. 仓库 Settings → Secrets and variables → Actions → New repository secret，分别添加：
   - `GMAIL_ADDRESS`：发送邮件的完整 Gmail 地址。
   - `GMAIL_APP_PASSWORD`：应用专用密码，不是 Google 登录密码。
   - `EMAIL_TO`：可选，接收邮箱；不填则发给发送邮箱自己。
5. Actions → Tibo email monitor → Run workflow，勾选 `test_email`，验证邮件送达（也查垃圾邮件）。
6. 再次运行，取消 `test_email`：首次成功读取后建立基线，不补发历史帖。以后自动定时检查，有新帖才发邮件。

## 行为和限制

- 包含作者原创、引用帖和回复，排除纯转发和时间线中的其他作者。一次检查发现多条时合并成一封邮件。
- 使用 FxEmbed 第三方公开接口，无 X Cookie 或 API key。接口可能失效、缓存或遗漏，无法保证全部帖子，也不监控编辑、删除和文章全文变化。接口今天可读不代表永久可用。
- GitHub schedule 可能延迟或漏调度；不是即时提醒。公开仓库长期无活动时，定时任务可能被自动停用，请定期检查 Actions。
- 仅使用公开仓库的标准 `ubuntu-latest` runner，不开通付费服务。GitHub 平台政策及账号限制仍适用。
- 持久状态在 `monitor-state` 分支。发送失败保留待发队列；若邮件已发送但状态未能提交，下一次可能重复发送。SMTP 无法提供严格的恰好一次投递。
- 删除 `monitor-state` 会丢失检查点，下一轮将重新建立基线。
- 停止：Actions → 工作流右上角菜单 → Disable workflow。撤销凭证：Google 应用专用密码页面删除对应密码。

## 本地验证（不会发送邮件）

```sh
python -m unittest -v
python monitor.py --dry-run
```

接口路径和过滤方式参考 MIT 项目 https://github.com/TerryYu12/codex-reset-signal 的文档；本目录为独立的 Python 实现。

官方参考：
- https://docs.github.com/en/actions/concepts/billing-and-usage
- https://docs.github.com/en/actions/how-tos/manage-workflow-runs/disable-and-enable-workflows
- https://support.google.com/accounts/answer/185833
