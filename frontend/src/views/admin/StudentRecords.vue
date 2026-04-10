<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import { useRoute } from 'vue-router';
import { useUsersStore } from '../../stores/users';

import BaseCard from '../../components/BaseCard.vue';
import BaseButton from '../../components/BaseButton.vue';
import AddPastSessionModal from '../../components/AddPastSessionModal.vue';
import type { User, Session, InstrumentRecord } from '../../types';
import axios from 'axios';

const route = useRoute();
const usersStore = useUsersStore();
// const scheduleStore = useScheduleStore();

const studentId = route.params.id as string;
const student = ref<User | null>(null);
const isLoading = ref(true);

const sessions = ref<Session[]>([]);
const showAddPastSession = ref(false);
const API_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

const filters = ref({
  status: 'all',
  instrument: 'all'
});

const fetchStudent = async () => {
  if (usersStore.users.length === 0) {
    await usersStore.fetchUsers();
  }
  student.value = usersStore.users.find((u: User) => String(u.id) === studentId) || null;
};

const fetchSessions = async () => {
  try {
    const res = await axios.get(`${API_URL}/sessions/student/${studentId}/records`);
    sessions.value = res.data.map((s: any) => ({
      id: String(s.id),
      studentId: String(s.student_id),
      teacherId: String(s.teacher_id),
      startTime: s.start_time,
      endTime: s.end_time,
      status: s.status,
      proposedBy: s.proposed_by ? String(s.proposed_by) : undefined,
      notes: s.notes,
      imageProofUrl: s.proof_image_url,
      homeworkAssigned: s.homework_assigned,
      homeworkCompleted: s.homework_completed,
      instrumentId: s.instrument_id,
      isManualEntry: s.is_manual_entry,
      sessionNumber: s.session_number
    }));
  } catch (err) {
    console.error("Failed to fetch sessions", err);
  }
};

onMounted(async () => {
  isLoading.value = true;
  await Promise.all([
    fetchStudent(),
    fetchSessions(),
    usersStore.instruments.length === 0 ? usersStore.fetchInstruments() : Promise.resolve()
  ]);
  isLoading.value = false;
});

const filteredSessions = computed(() => {
  return sessions.value.filter((s: Session) => {
    if (filters.value.status !== 'all' && s.status !== filters.value.status) return false;
    if (filters.value.instrument !== 'all' && s.instrumentId !== Number(filters.value.instrument)) return false;
    return true;
  });
});

const totalEnrolled = computed(() => student.value?.sessionsEnrolled || 0);
const totalUsed = computed(() => {
  return sessions.value.filter((s: Session) => s.status === 'completed').length;
});
const progressPercentage = computed(() => {
  if (totalEnrolled.value === 0) return 0;
  return Math.min(100, Math.round((totalUsed.value / totalEnrolled.value) * 100));
});

const getInstrumentName = (id?: number) => {
  if (!id) return 'Unknown';
  return usersStore.instruments.find((i: InstrumentRecord) => i.id === id)?.name || 'Unknown';
};

const getTeacherName = (id: string) => {
  return usersStore.users.find((u: User) => String(u.id) === id)?.name || 'Unknown';
};

const formatDate = (dateStr: string) => {
  return new Date(dateStr).toLocaleDateString('en-US', {
    weekday: 'short', month: 'short', day: 'numeric', year: 'numeric'
  });
};

const handleSessionAdded = () => {
  fetchSessions();
  // We'd ideally update user's sessionsLeft here, but for now we just refetch
};
</script>

<template>
  <div class="space-y-8 max-w-[1600px] mx-auto pb-12 px-4 sm:px-6">
    <!-- Header/Profile Info -->
    <section v-if="student" class="flex flex-col md:flex-row gap-6 items-start">
      <BaseCard class="flex-1 p-6 liquid-glass border border-white/10 relative overflow-hidden group">
        <div class="flex items-center gap-6">
          <div class="w-24 h-24 rounded-full bg-surface-container-highest border border-outline-variant flex items-center justify-center overflow-hidden flex-shrink-0 relative">
            <img v-if="student.avatarUrl" :src="student.avatarUrl" alt="Avatar" class="w-full h-full object-cover" />
            <span v-else class="material-symbols-outlined text-4xl text-on-surface-variant">person</span>
          </div>
          <div>
            <h1 class="text-3xl font-black text-white tracking-tight">{{ student.name }}</h1>
            <p class="text-white/60 text-sm flex gap-2 items-center mt-1">
              <span class="material-symbols-outlined text-xs">mail</span> {{ student.email }}
            </p>
            <div class="flex flex-wrap gap-2 mt-3">
               <span v-for="inst in student.instruments" :key="inst.id" class="px-2.5 py-1 rounded-md bg-white/5 border border-white/10 text-xs font-bold text-white/80 uppercase tracking-widest">
                 {{ inst.name }}
               </span>
            </div>
          </div>
        </div>
      </BaseCard>

      <BaseCard class="w-full md:w-80 p-6 liquid-glass border border-white/10 shrink-0">
        <h3 class="text-sm font-black uppercase tracking-[0.2em] text-white/50 mb-4">Enrollment Status</h3>
        <div class="space-y-4">
          <div>
            <div class="flex justify-between text-sm mb-1">
              <span class="text-white/70">Progress</span>
              <span class="font-bold text-white">{{ totalUsed }} / {{ totalEnrolled }}</span>
            </div>
            <div class="w-full h-2 bg-white/10 rounded-full overflow-hidden">
              <div class="h-full bg-primary transition-all duration-1000" :style="{ width: `${progressPercentage}%` }"></div>
            </div>
          </div>
          <div class="flex justify-between items-center pt-2 border-t border-white/5">
             <span class="text-xs text-white/50">Sessions Left</span>
             <span class="text-xl font-black text-primary">{{ student.sessionsLeft || 0 }}</span>
          </div>
        </div>
      </BaseCard>
    </section>

    <!-- Controls -->
    <section class="flex flex-col sm:flex-row justify-between items-center gap-4">
      <div class="flex gap-4 w-full sm:w-auto">
        <select v-model="filters.status" class="bg-surface-container-highest/50 border border-outline-variant/30 text-on-surface rounded-xl px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/20">
          <option value="all">All Statuses</option>
          <option value="completed">Completed</option>
          <option value="scheduled">Scheduled</option>
          <option value="cancelled">Cancelled</option>
        </select>
        <select v-model="filters.instrument" class="bg-surface-container-highest/50 border border-outline-variant/30 text-on-surface rounded-xl px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/20">
          <option value="all">All Instruments</option>
          <option v-for="inst in usersStore.instruments" :key="inst.id" :value="inst.id">{{ inst.name }}</option>
        </select>
      </div>

      <BaseButton @click="showAddPastSession = true" class="w-full sm:w-auto">
        <span class="material-symbols-outlined mr-2">history_edu</span> Add Past Session
      </BaseButton>
    </section>

    <!-- Timeline -->
    <section>
      <div v-if="isLoading" class="flex justify-center p-12">
        <span class="material-symbols-outlined animate-spin text-primary text-4xl">autorenew</span>
      </div>
      <div v-else-if="filteredSessions.length === 0" class="text-center p-12 border border-dashed border-white/20 rounded-2xl text-white/50">
        <span class="material-symbols-outlined text-5xl mb-2 opacity-50">event_busy</span>
        <p>No session records found.</p>
      </div>
      <div v-else class="space-y-4">
        <BaseCard v-for="session in filteredSessions" :key="session.id" class="p-5 liquid-glass border border-white/10 hover:border-white/20 transition-colors">
          <div class="flex flex-col md:flex-row gap-4 justify-between md:items-center">

            <div class="flex items-start gap-4">
              <div class="w-12 h-12 rounded-xl bg-white/5 flex items-center justify-center shrink-0 border border-white/10">
                <span class="material-symbols-outlined text-primary" v-if="session.status === 'completed'">check_circle</span>
                <span class="material-symbols-outlined text-secondary" v-else-if="session.status === 'scheduled'">event</span>
                <span class="material-symbols-outlined text-white/50" v-else>cancel</span>
              </div>

              <div>
                <div class="flex items-center gap-2 mb-1">
                  <h4 class="font-bold text-white">{{ formatDate(session.startTime) }}</h4>
                  <span v-if="session.isManualEntry" class="px-2 py-0.5 rounded text-[10px] uppercase font-bold tracking-widest bg-orange-500/20 text-orange-400 border border-orange-500/30">Paper Record</span>
                  <span v-if="session.sessionNumber" class="text-xs text-white/40">#{{ session.sessionNumber }}</span>
                </div>

                <div class="text-sm text-white/60 flex flex-wrap gap-x-4 gap-y-1 items-center">
                  <span class="flex items-center gap-1"><span class="material-symbols-outlined text-[14px]">person</span> {{ getTeacherName(session.teacherId) }}</span>
                  <span class="flex items-center gap-1"><span class="material-symbols-outlined text-[14px]">music_note</span> {{ getInstrumentName(session.instrumentId) }}</span>
                </div>

                <p v-if="session.notes" class="text-sm text-white/80 mt-3 pl-3 border-l-2 border-primary/30 italic">
                  "{{ session.notes }}"
                </p>
              </div>
            </div>

            <div class="flex items-center gap-3">
               <span class="text-xs font-bold uppercase tracking-widest px-3 py-1 rounded-full border"
                 :class="{
                   'border-primary/30 text-primary bg-primary/10': session.status === 'completed',
                   'border-secondary/30 text-secondary bg-secondary/10': session.status === 'scheduled',
                   'border-white/20 text-white/50': !['completed', 'scheduled'].includes(session.status)
                 }">
                 {{ session.status }}
               </span>
            </div>

          </div>
        </BaseCard>
      </div>
    </section>

    <AddPastSessionModal
      v-if="student"
      :is-open="showAddPastSession"
      :student="student"
      @close="showAddPastSession = false"
      @created="handleSessionAdded"
    />
  </div>
</template>
