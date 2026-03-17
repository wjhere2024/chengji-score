# 成绩管理独立版

这个目录是从 `F:\test\chengji` 中抽出的成绩子系统。当前推荐以“代码模型 + Django 迁移”作为唯一标准初始化数据库。

## 当前功能

- 教师 / 管理员登录
- 学校、班级、学生、科目、考试、成绩管理
- 学生批量导入
- 成绩 Excel / CSV 批量导入
- 成绩文本批量录入
- 成绩模板下载
- 成绩统计

## 目录结构

- `backend/` Django 后端
- `frontend/` Vue 管理台

## 本地启动

后端：

```powershell
cd F:\test\chengji-score\backend
python manage.py runserver
```

前端：

```powershell
cd F:\test\chengji-score\frontend
npm install
npm run dev
```

## 推荐初始化方式

推荐直接新建数据库并执行迁移。

如果使用 SQLite，本地可以这样做：

```powershell
cd F:\test\chengji-score\backend
Remove-Item .\db.sqlite3 -ErrorAction SilentlyContinue
python manage.py migrate
python manage.py seed_demo_data
```

## 仓库自带演示库

仓库当前自带的 `backend/db.sqlite3` 已经是重新迁移并灌入演示数据后的版本，和当前代码表结构匹配，可直接用于演示。

当前演示数据包括：

- 学校：`名著书院`
- 班级：`红楼班`、`西游班`、`水浒班`、`三国班`、`诗经班`、`山海班`
- 学生：72 名，基于中国古典名著 / 古籍人物生成
- 考试：`春季学情诊断`、`期中素养测评`
- 成绩：624 条演示成绩

默认演示管理员账号：

- 用户名：`demo_admin`
- 密码：`demo123456`

如果需要重建演示学校数据：

```powershell
cd F:\test\chengji-score\backend
python manage.py seed_demo_data --reset
```

## 文本批量录入说明

成绩录入页支持“文本批量录入”，适合配合手机语音输入法使用。

示例：

```text
贾宝玉 95
林黛玉 98
jiabaoyu 96
jby 94
```

支持的匹配方式：

- 姓名精确匹配
- 全拼匹配
- 拼音首字母匹配

录入时会先解析预览，再确认导入。

## 已开放接口

- `/api/auth/login/`
- `/api/users/`
- `/api/schools/`
- `/api/classes/`
- `/api/students/`
- `/api/subjects/`
- `/api/exams/`
- `/api/scores/`

## 前端页面

- `/login`
- `/students`
- `/exams`
- `/score-entry`
- `/scores`
