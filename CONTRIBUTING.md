# Contributing

## Git Hooks

clone 후 한 번 아래 명령을 실행하면, 커밋할 때 `.githooks/pre-commit`이 `.pre-commit-config.yaml`에 정의된 검사(ruff, pytest 등)를 실행합니다.

```bash
git config core.hooksPath .githooks
```
