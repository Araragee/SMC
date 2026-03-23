#!/bin/bash
BASE="http://localhost:8000"
TOKEN=$(curl -s -X POST "$BASE/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin@example.com&password=password123" \
  | python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token',''))")

curl -s -X POST "$BASE/enrollments/" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"student_id":7,"teacher_id":2,"sessions_purchased":15,"sessions_used":2}'
