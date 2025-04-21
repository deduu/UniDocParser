# 🛠 Engineer Onboarding Guide

Welcome aboard! Here's how to get started working on this repository.

## ✅ Access

You've been added as a **collaborator**. That means you can:
- Clone the repo
- Create branches
- Push branches
- Open Pull Requests

## 🔁 Git Workflow

### 1. Clone the repo
```bash
git clone https://github.com/<org-or-user>/<repo-name>.git
cd <repo-name>
```

### 2. Create your branch (from main)
```bash
git checkout main
git pull origin main
git checkout -b feature/<your-feature-name>
```

### 3. Work on your code and commit
```bash
git add .
git commit -m "feat: add your feature"
```

### 4. Push your branch
```bash
git push origin feature/<your-feature-name>
```

### 5. Open a Pull Request (PR)
- Go to GitHub → Pull Requests → New Pull Request
- Set base = main and compare = your feature branch
- Use the PR template
- Request a review

## 💡 Tips
- Pull from main often and rebase to avoid conflicts
- Use meaningful commit messages
- Ask if you're unsure — we're all learning!

## 🧠 Team Git Workflow

We follow a branch-based Git workflow to keep our `main` branch stable.

### 🔄 Branching Strategy
- `main`: Production-ready. Protected. Only updated via PR.
- `feature/*`: New features
- `bugfix/*`: Fixing issues
- `refactor/*`: Internal code improvements

### 📤 Making Changes
1. Branch off `main`
2. Make changes & commit
3. Push your branch
4. Open a Pull Request
5. Get review
6. Merge PR (squash recommended)

### 🔒 Branch Protection Rules
- ✅ No direct push to `main`
- ✅ Require PR review
- ✅ Require status checks (if enabled)
- ✅ Allow squash merges only

### 🧪 CI/CD (if applicable)
- Auto runs lint/tests
- Blocks PR if checks fail

## 📄 PR Template

When creating a pull request, use this template:

```yaml
## Description
<!-- What does this PR do? -->

## Related Issues
<!-- Link to related issues using #issue-number -->

## Testing
<!-- How was this change tested? -->

## Screenshots
<!-- For UI changes -->

## Checklist
- [ ] Tests added/updated
- [ ] Documentation updated
- [ ] Self-reviewed
```

---

Stay clean. Stay collaborative. Let's build something great 🚀

