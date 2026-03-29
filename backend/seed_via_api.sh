#!/bin/bash
# Seed script via API — run while uvicorn is running
# Usage: bash backend/seed_via_api.sh

BASE="http://localhost:8000"

echo "🔐 Getting admin token..."
TOKEN=$(curl -s -X POST "$BASE/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin@example.com&password=password123" \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('access_token',''))")

if [ -z "$TOKEN" ]; then
  echo "❌ Could not get admin token. Is the server running?"
  exit 1
fi
echo "✅ Got token"

# Get existing roles
echo ""
echo "📋 Fetching roles..."
ROLES=$(curl -s "$BASE/roles/" -H "Authorization: Bearer $TOKEN")
echo "$ROLES"

# Helper to get role_id by name
get_role_id() {
  echo "$ROLES" | python3 -c "
import sys, json
name='$1'
roles=json.load(sys.stdin)
r=[x for x in roles if x['name']==name]
print(r[0]['id'] if r else '')
"
}

TEACHER_ROLE=$(get_role_id "teacher")
STUDENT_ROLE=$(get_role_id "student")
echo "Teacher role ID: $TEACHER_ROLE"
echo "Student role ID: $STUDENT_ROLE"

create_user() {
  local name="$1" email="$2" role_id="$3" sessions_left="${4:-0}"
  # Check if user exists first
  EXISTING=$(curl -s "$BASE/debug/users" | python3 -c "
import sys,json
data=json.load(sys.stdin)
print(next((str(u) for u in data if u.get('email')=='$email'), ''))")
  if [ -n "$EXISTING" ]; then
    echo "  ⚡ Exists: $email"
    return
  fi
  curl -s -X POST "$BASE/users/" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $TOKEN" \
    -d "{\"name\":\"$name\",\"email\":\"$email\",\"password\":\"password123\",\"role_id\":$role_id,\"sessions_left\":$sessions_left}" \
    | python3 -c "import sys,json; d=json.load(sys.stdin); print('  ✅ Created:', d.get('email','ERROR'), d.get('id',''))"
}

echo ""
echo "👩‍🏫 Creating teachers..."
create_user "Dr. Sarah Jenkins"  "sarah.jenkins@smc.edu"  $TEACHER_ROLE 0
create_user "Marcus Vane"         "marcus.vane@smc.edu"    $TEACHER_ROLE 0
create_user "Dr. Eleanor Rigby"   "eleanor.rigby@smc.edu"  $TEACHER_ROLE 0
create_user "Arthur Brown"        "arthur.brown@smc.edu"   $TEACHER_ROLE 0
create_user "Dr. Aris Thorne"     "aris.thorne@smc.edu"    $TEACHER_ROLE 0

echo ""
echo "🎓 Creating students..."
create_user "Elena Rodriguez"  "elena.rodriguez@smc.edu"  $STUDENT_ROLE 10
create_user "Julian Chen"      "julian.chen@smc.edu"      $STUDENT_ROLE 10
create_user "Sarah Mitchell"   "sarah.mitchell@smc.edu"   $STUDENT_ROLE 10

echo ""
echo "📅 Creating sessions..."

# Get user IDs
get_user_id() {
  curl -s "$BASE/users/role/$1" -H "Authorization: Bearer $TOKEN" \
    | python3 -c "
import sys,json
users=json.load(sys.stdin)
matches=[u for u in users if u.get('email')=='$2']
print(matches[0]['id'] if matches else '')
"
}

SARAH_ID=$(get_user_id "teacher" "sarah.jenkins@smc.edu")
MARCUS_ID=$(get_user_id "teacher" "marcus.vane@smc.edu")
ELEANOR_ID=$(get_user_id "teacher" "eleanor.rigby@smc.edu")
ARTHUR_ID=$(get_user_id "teacher" "arthur.brown@smc.edu")
ARIS_ID=$(get_user_id "teacher" "aris.thorne@smc.edu")
ELENA_ID=$(get_user_id "student" "elena.rodriguez@smc.edu")
JULIAN_ID=$(get_user_id "student" "julian.chen@smc.edu")
SARAH_S_ID=$(get_user_id "student" "sarah.mitchell@smc.edu")

echo "Teachers: $SARAH_ID $MARCUS_ID $ELEANOR_ID $ARTHUR_ID $ARIS_ID"
echo "Students: $ELENA_ID $JULIAN_ID $SARAH_S_ID"

create_session() {
  local t_id="$1" s_id="$2" start="$3" end="$4" status="$5"
  # Get a teacher token
  local T_TOKEN=$(curl -s -X POST "$BASE/login" \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -d "username=$6&password=password123" \
    | python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token',''))")
  curl -s -X POST "$BASE/sessions/" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $T_TOKEN" \
    -d "{\"teacher_id\":$t_id,\"student_id\":$s_id,\"start_time\":\"$start\",\"end_time\":\"$end\",\"status\":\"$status\"}" \
    | python3 -c "import sys,json; d=json.load(sys.stdin); print('  ✅ Session', d.get('id','?'), d.get('status','?'))" 2>/dev/null
}

# Elena <-> Sarah (completed)
create_session $SARAH_ID $ELENA_ID "2026-03-15T09:00:00" "2026-03-15T10:00:00" "completed" "sarah.jenkins@smc.edu"
create_session $SARAH_ID $ELENA_ID "2026-03-22T09:00:00" "2026-03-22T10:00:00" "scheduled" "sarah.jenkins@smc.edu"
# Elena <-> Marcus
create_session $MARCUS_ID $ELENA_ID "2026-03-16T11:00:00" "2026-03-16T12:00:00" "completed" "marcus.vane@smc.edu"
create_session $MARCUS_ID $ELENA_ID "2026-03-23T11:00:00" "2026-03-23T12:00:00" "scheduled" "marcus.vane@smc.edu"
# Julian <-> Eleanor (completed)
create_session $ELEANOR_ID $JULIAN_ID "2026-03-14T14:00:00" "2026-03-14T15:00:00" "completed" "eleanor.rigby@smc.edu"
create_session $ELEANOR_ID $JULIAN_ID "2026-03-22T14:00:00" "2026-03-22T15:00:00" "scheduled" "eleanor.rigby@smc.edu"
# Julian <-> Arthur
create_session $ARTHUR_ID $JULIAN_ID "2026-03-17T10:00:00" "2026-03-17T11:00:00" "completed" "arthur.brown@smc.edu"
create_session $ARTHUR_ID $JULIAN_ID "2026-03-24T10:00:00" "2026-03-24T11:00:00" "scheduled" "arthur.brown@smc.edu"
# Sarah M <-> Aris
create_session $ARIS_ID $SARAH_S_ID "2026-03-13T15:00:00" "2026-03-13T16:00:00" "completed" "aris.thorne@smc.edu"
create_session $ARIS_ID $SARAH_S_ID "2026-03-22T15:00:00" "2026-03-22T16:00:00" "scheduled" "aris.thorne@smc.edu"
# More sessions for variety
create_session $SARAH_ID $JULIAN_ID "2026-03-18T09:00:00" "2026-03-18T10:00:00" "scheduled" "sarah.jenkins@smc.edu"
create_session $MARCUS_ID $SARAH_S_ID "2026-03-19T13:00:00" "2026-03-19T14:00:00" "scheduled" "marcus.vane@smc.edu"
create_session $ELEANOR_ID $ELENA_ID "2026-03-20T16:00:00" "2026-03-20T17:00:00" "scheduled" "eleanor.rigby@smc.edu"
create_session $ARTHUR_ID $SARAH_S_ID "2026-03-25T11:00:00" "2026-03-25T12:00:00" "scheduled" "arthur.brown@smc.edu"
create_session $ARIS_ID $JULIAN_ID "2026-03-26T14:00:00" "2026-03-26T15:00:00" "scheduled" "aris.thorne@smc.edu"

echo ""
echo "🎉 Seeding complete!"
echo ""
echo "Login credentials (password: password123):"
echo "  admin@example.com      → Admin"
echo "  sarah.jenkins@smc.edu  → Teacher"
echo "  marcus.vane@smc.edu    → Teacher"
echo "  eleanor.rigby@smc.edu  → Teacher"
echo "  arthur.brown@smc.edu   → Teacher"
echo "  aris.thorne@smc.edu    → Teacher"
echo "  elena.rodriguez@smc.edu → Student"
echo "  julian.chen@smc.edu     → Student"
echo "  sarah.mitchell@smc.edu  → Student"
