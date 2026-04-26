---
title: REST API Reference - OpenMLR
description: OpenMLR REST API documentation. Authentication, conversations, messaging, paper management, settings, and SSE streaming endpoints.
---

# REST API

All endpoints are prefixed with `/api`. Authentication uses JWT Bearer tokens.

## Auth

| Method | Path | Body | Description |
|--------|------|------|-------------|
| POST | `/api/auth/register` | `{username, password, display_name?}` | Create account, returns token |
| POST | `/api/auth/login` | `{username, password}` | Login, returns token |
| GET | `/api/auth/me` | — | Current user info |
| GET | `/api/auth/check` | — | Check if any users exist (onboarding) |

## Conversations

| Method | Path | Body | Description |
|--------|------|------|-------------|
| GET | `/api/conversations` | — | List all conversations |
| POST | `/api/conversations` | `{title?, model?, mode?}` | Create conversation |
| GET | `/api/conversations/:uuid` | — | Get conversation + messages |
| DELETE | `/api/conversations/:uuid` | — | Delete conversation |

## Messaging

| Method | Path | Body | Description |
|--------|------|------|-------------|
| POST | `/api/message` | `{message, mode?}` | Send message (mode: plan/execute) |
| POST | `/api/answers` | `{answers: {qid: label}}` | Answer structured questions |
| POST | `/api/interrupt` | — | Cancel current agent turn (Redis relay) |
| POST | `/api/approval` | `{approvals: {id: bool}}` | Approve/reject tool calls |
| POST | `/api/undo` | — | Undo last turn |
| POST | `/api/compact` | — | Compact conversation context |
| POST | `/api/model` | `{model}` | Switch LLM model (sticky, persisted) |

## SSE

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/events?token=JWT` | Server-Sent Events stream (supports reconnection catch-up) |

## Settings

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/settings` | All settings |
| GET | `/api/settings/:category` | Settings by category |
| PUT | `/api/settings/:category/:key` | Update setting |
| DELETE | `/api/settings/:category/:key` | Delete setting |
| GET | `/api/providers` | List provider status |
| GET | `/api/models` | List available models |
| GET | `/api/status` | Current model + config |

## Frontend Routes

The frontend is a single-page app served from `/`:

| Route | Description |
|-------|-------------|
| `/login` | Authentication |
| `/` | Chat UI (protected, redirects to `/login` if unauthenticated) |
| `/:uuid` | Specific conversation |
| `/settings/providers` | API key management |
| `/settings/agent` | Model & behavior settings |
| `/settings/sandbox` | Execution environment settings |
| `/settings/writing` | Paper writing preferences |

## Health

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | `{"status": "ok", "version": "0.2.0"}` |
