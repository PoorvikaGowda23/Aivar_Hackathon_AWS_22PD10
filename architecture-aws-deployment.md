# AWS Cloud Deployment & CI/CD Architecture

This diagram shows how code goes from a `git push` to a live, running deployment, and which external cloud services the running app depends on.

```mermaid
flowchart TD
    subgraph Dev["Developer Workflow"]
        A["Developer pushes code<br/>git push origin main"]
    end

    subgraph Source["GitHub"]
        B["GitHub Repository<br/>PoorvikaGowda23/Aivar_Hackathon_AWS_22PD10<br/>Branch: main"]
    end

    subgraph Pipeline["AWS CodePipeline"]
        C["Source Stage<br/>GitHub App connection"]
        D["Deploy Stage<br/>Elastic Beanstalk target"]
    end

    subgraph Runtime["AWS Elastic Beanstalk"]
        E["Environment: agent-compliance-card-generator<br/>Platform: Python 3.11, Amazon Linux 2023"]
        F["EC2 Instance(s)<br/>Uvicorn + FastAPI app"]
        G["Environment Properties:<br/>DATABASE_URL, GROQ_API_KEY, LOG_LEVEL"]
        H["Health Endpoints<br/>/health (liveness)<br/>/health?full=true (deep check)"]
    end

    subgraph External["External Managed Services"]
        I["Neon Serverless PostgreSQL<br/>Immutable card version storage"]
        J["Groq API<br/>LLaMA 3.3 70B / Qwen inference"]
    end

    A --> B
    B --> C
    C --> D
    D --> E
    E --> F
    G --> F
    F --> H
    F -->|SQLAlchemy| I
    F -->|HTTPS| J

    classDef devStyle fill:#EDEDF2,stroke:#B0B0C0,stroke-width:1.5px,color:#3A3A46
    classDef sourceStyle fill:#DCEAF7,stroke:#8FB8DC,stroke-width:1.5px,color:#2A4A66
    classDef pipelineStyle fill:#E3DDF4,stroke:#B3A2E0,stroke-width:1.5px,color:#42305F
    classDef runtimeStyle fill:#DDF0E4,stroke:#8FCBA8,stroke-width:1.5px,color:#245C3A
    classDef externalStyle fill:#FBE1E8,stroke:#E39DB2,stroke-width:1.5px,color:#6B2E43

    class A devStyle
    class B sourceStyle
    class C,D pipelineStyle
    class E,F,G,H runtimeStyle
    class I,J externalStyle

    style Dev fill:#F5F5F8,stroke:#D0D0D8,stroke-width:1px
    style Source fill:#F0F6FB,stroke:#C5DCEE,stroke-width:1px
    style Pipeline fill:#F3F0FA,stroke:#D6CCEE,stroke-width:1px
    style Runtime fill:#F0F9F3,stroke:#C6E7D3,stroke-width:1px
    style External fill:#FCEEF1,stroke:#F0CCD8,stroke-width:1px
```

## Flow Summary

| Step | Component | Role |
| :--- | :--- | :--- |
| 1 | Developer | Pushes committed code to `main` branch on GitHub |
| 2 | GitHub | Hosts source; triggers CodePipeline via GitHub App connection |
| 3 | AWS CodePipeline | Source stage pulls latest commit; Deploy stage ships it to Beanstalk (build stage skipped) |
| 4 | AWS Elastic Beanstalk | Provisions/updates EC2 instance(s) running Python 3.11 + Uvicorn + FastAPI, zero-downtime deploy |
| 5 | Environment Properties | Injects `DATABASE_URL`, `GROQ_API_KEY`, `LOG_LEVEL` as runtime env vars |
| 6 | Neon Postgres | External managed DB storing immutable compliance card versions |
| 7 | Groq API | External LLM inference for narrative synthesis and AI Regulatory Auditor review |
| 8 | Health Checks | `/health` for cloud monitor liveness, `/health?full=true` for deep dependency checks (DB + Groq latency) |
