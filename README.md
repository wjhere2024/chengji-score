# 成绩管理独立版

这个目录是从 `F:\test\chengji` 中抽出的成绩子系统，当前建议按“代码模型 + Django 迁移”作为唯一标准来初始化数据库，不再继续沿用旧项目复制出来的 `db.sqlite3`。

## 当前功能

- 教师 / 管理员登录
- 学校、班级、学生、科目、考试、成绩管理
- 学生批量导入
- 成绩批量导入
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

不要继续复用旧库。推荐直接新建数据库并执行迁移。

如果使用 SQLite，本地可以这样做：

```powershell
cd F:\test\chengji-score\backend
Remove-Item .\db.sqlite3 -ErrorAction SilentlyContinue
python manage.py migrate
python manage.py seed_demo_data
```

完成后会创建一套可演示数据：

- 学校：`名著书院`
- 班级：`红楼班`、`西游班`、`水浒班`、`三国班`、`诗经班`、`山海班`
- 学生：按中国古典名著 / 古籍人物生成
- 考试：`春季学情诊断`、`期中素养测评`
- 成绩：按班级和科目自动生成演示成绩

默认演示管理员账号：

- 用户名：`demo_admin`
- 密码：`demo123456`

如果需要重建演示学校数据：

```powershell
cd F:\test\chengji-score\backend
python manage.py seed_demo_data --reset
```

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

## 备注

仓库当前自带的旧 `backend/db.sqlite3` 来自原项目，表结构与当前代码并不完全同步。对外交付时，建议始终使用迁移重新建库，再执行 `seed_demo_data` 生成演示环境。
