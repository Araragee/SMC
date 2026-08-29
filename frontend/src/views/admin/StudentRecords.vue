<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import { useRoute } from 'vue-router';
import { useUsersStore } from '@stores/users';
import { useScheduleStore } from '@stores/schedule';
import { useInteractionsStore } from '@stores/interactions';

import BaseCard from '@components/BaseCard.vue';
import BaseDropdown from '@/components/BaseDropdown.vue';
import BaseButton from '@components/BaseButton.vue';
import AddPastSessionModal from '@components/AddPastSessionModal.vue';
import type { User, Session, InstrumentRecord, Enrollment } from '@types';
import { useDialog } from '@composables/useDialog';

const route = useRoute();
const usersStore = useUsersStore();
const scheduleStore = useScheduleStore();
const interactionsStore = useInteractionsStore();
const dialog = useDialog();

const studentId = Number(route.params.id);
const student = ref<User | null>(null);
const isLoading = ref(true);

const showAddPastSession = ref(false);

const filters = ref({
  status: 'all',
  instrument: 'all'
});

const fetchStudent = async () => {
  if (usersStore.users.length === 0) {
    await usersStore.fetchUsers();
  }
  student.value = usersStore.users.find((u: User) => u.id === studentId) || null;
};

const fetchSessions = async () => {
  await scheduleStore.fetchStudentRecords(studentId);
};

onMounted(async () => {
  isLoading.value = true;
  await Promise.all([
    fetchStudent(),
    fetchSessions(),
    interactionsStore.fetchStudentEnrollments(studentId),
    usersStore.instruments.length === 0 ? usersStore.fetchInstruments() : Promise.resolve()
  ]);
  isLoading.value = false;
});

const filteredSessions = computed(() => {
  return scheduleStore.getSessionsByStudentId(studentId).filter((s: Session) => {
    if (filters.value.status !== 'all' && s.status !== filters.value.status) return false;
    if (filters.value.instrument !== 'all' && s.instrumentId !== Number(filters.value.instrument)) return false;
    return true;
  }).sort((a: any, b: any) => new Date(b.startTime).getTime() - new Date(a.startTime).getTime());
});

const totalEnrolled = computed(() => student.value?.sessionsEnrolled || 0);
const totalUsed = computed(() => {
  return scheduleStore.getSessionsByStudentId(studentId).filter((s: Session) => s.status === 'completed').length;
});
const progressPercentage = computed(() => {
  if (totalEnrolled.value === 0) return 0;
  return Math.min(100, Math.round((totalUsed.value / totalEnrolled.value) * 100));
});

const getInstrumentName = (id?: number) => {
  if (!id) return 'Unknown';
  return usersStore.instruments.find((i: InstrumentRecord) => i.id === id)?.name || 'Unknown';
};

const getTeacherName = (id: number) => {
  return usersStore.users.find((u: User) => u.id === id)?.name || 'Unknown';
};

const formatDate = (dateStr: string) => {
  return new Date(dateStr).toLocaleDateString('en-US', {
    weekday: 'short', month: 'short', day: 'numeric', year: 'numeric'
  });
};

const handleSessionAdded = () => {
  fetchSessions();
};

const handleDeleteEnrollment = async (enrollment: Enrollment) => {
  const teacherName = usersStore.users.find((u: User) => u.id === enrollment.teacherId)?.name || `Teacher #${enrollment.teacherId}`;
  const ok = await dialog.confirm(
    `Remove this enrollment with ${teacherName}? Unused sessions (${enrollment.sessionsPurchased - enrollment.sessionsUsed}) will be rolled back from the student's balance.`,
    { title: 'Delete Enrollment', destructive: true }
  );
  if (!ok) return;
  await interactionsStore.deleteEnrollment(enrollment.id);
  await interactionsStore.fetchStudentEnrollments(studentId);
  await fetchStudent();
};

const handleRecalculate = async () => {
  const result = await interactionsStore.recalculateSessions(studentId);
  if (result !== null) await fetchStudent();
};
</script>

<template>
  <div class="space-y-8 max-w-[1600px] mx-auto pb-12 px-4 sm:px-6">
    <!-- Header/Profile Info -->
    <section v-if="student" class="flex flex-col md:flex-row gap-6 items-start">
      <BaseCard class="flex-1 p-6 liquid-glass border border-on-surface/10 relative overflow-hidden group">
        <div class="flex items-center gap-6">
          <div class="size-24 rounded-full bg-surface-container-highest border border-outline-variant flex items-center justify-center overflow-hidden flex-shrink-0 relative">
            <img v-if="student.avatarUrl" :src="student.avatarUrl" alt="Avatar" class="w-full h-full object-cover" />
            <span v-else class="material-symbols-outlined text-4xl text-on-surface-variant">person</span>
          </div>
          <div>
            <h1 class="text-3xl font-semibold text-on-surface tracking-tight">{{ student.name }}</h1>
            <p class="text-on-surface/60 text-sm flex gap-2 items-center mt-1">
              <span class="material-symbols-outlined text-xs">mail</span> {{ student.email }}
            </p>
            <div class="flex flex-wrap gap-2 mt-3">
               <span v-for="inst in student.instruments" :key="inst.id" class="px-2 py-1 rounded-md bg-on-surface/5 border border-on-surface/10 text-xs font-bold text-on-surface/80 uppercase">
                 {{ inst.name }}
               </span>
            </div>
          </div>
        </div>
      </BaseCard>

      <BaseCard class="w-full md:w-80 p-6 liquid-glass border border-on-surface/10 shrink-0">
        <h3 class="text-sm font-semibold uppercase text-on-surface/50 mb-4">Enrollment Status</h3>
        <div class="space-y-4">
          <div>
            <div class="flex justify-between text-sm mb-1">
              <span class="text-on-surface/70">Progress</span>
              <span class="font-bold text-on-surface">{{ totalUsed }} / {{ totalEnrolled }}</span>
            </div>
            <div class="w-full h-2 bg-on-surface/10 rounded-full overflow-hidden">
              <div class="h-full bg-primary transition-all" :style="{ width: `${progressPercentage}%` }"></div>
            </div>
          </div>
          <div class="flex justify-between items-center pt-2 border-t border-on-surface/5">
             <span class="text-xs text-on-surface/50">Sessions Left</span>
             <span class="text-xl font-semibold text-primary">{{ student.sessionsLeft || 0 }}</span>
          </div>
          <button
            class="w-full mt-1 flex items-center justify-center gap-2 text-xs font-bold uppercase text-on-surface/50 hover:text-primary border border-on-surface/10 hover:border-primary/30 rounded-xl py-2 transition-all"
            :disabled="interactionsStore.isLoading"
            @click="handleRecalculate"
          >
            <span class="material-symbols-outlined text-sm">sync</span>
            Recalculate Balance
          </button>
        </div>
      </BaseCard>
    </section>

    <!-- Enrollments -->
    <section v-if="interactionsStore.enrollments.length > 0">
      <h2 class="text-xs font-semibold uppercase text-on-surface/40 mb-3">Enrollments</h2>
      <div class="space-y-2">
        <BaseCard
          v-for="enrollment in interactionsStore.enrollments"
          :key="enrollment.id"
          class="p-4 liquid-glass border border-on-surface/10 flex flex-col sm:flex-row sm:items-center justify-between gap-3"
        >
          <div class="flex items-center gap-3">
            <span class="material-symbols-outlined text-primary/70 text-lg">school</span>
            <div>
              <p class="font-bold text-sm text-on-surface">
                {{ usersStore.users.find((u: User) => u.id === enrollment.teacherId)?.name || `Teacher #${enrollment.teacherId}` }}
              </p>
              <p class="text-xs text-on-surface/50 mt-0.5">
                {{ enrollment.sessionsUsed }} used · {{ enrollment.sessionsPurchased - enrollment.sessionsUsed }} remaining of {{ enrollment.sessionsPurchased }} purchased
              </p>
            </div>
          </div>
          <button
            class="flex items-center gap-1.5 text-xs font-bold text-error/70 hover:text-error border border-error/20 hover:border-error/40 rounded-xl px-3 py-1.5 transition-all shrink-0"
            :disabled="interactionsStore.isLoading"
            @click="handleDeleteEnrollment(enrollment)"
          >
            <span class="material-symbols-outlined text-sm">delete</span>
            Remove
          </button>
        </BaseCard>
      </div>
    </section>

    <!-- Controls -->
    <section class="flex flex-col sm:flex-row justify-between items-center gap-4">
      <div class="flex gap-4 w-full sm:w-auto">
        <BaseDropdown v-model="filters.status" :options="[{ value: 'all', label: 'All Statuses' }, { value: 'completed', label: 'Completed' }, { value: 'scheduled', label: 'Scheduled' }, { value: 'cancelled', label: 'Cancelled' }]" />
        <BaseDropdown v-model="filters.instrument" :options="[{ value: 'all', label: 'All Instruments' }, ...usersStore.instruments.map(inst => ({ value: inst.id, label: inst.name }))]" />
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
      <div v-else-if="filteredSessions.length === 0" class="text-center p-12 border border-dashed border-on-surface/20 rounded-2xl text-on-surface/50">
        <span class="material-symbols-outlined text-5xl mb-2 opacity-50">event_busy</span>
        <p>No session records found.</p>
      </div>
      <div v-else class="space-y-4">
        <BaseCard v-for="session in filteredSessions" :key="session.id" class="p-4 liquid-glass border border-on-surface/10 hover:border-on-surface/20 transition-colors">
          <div class="flex flex-col md:flex-row gap-4 justify-between md:items-center">

            <div class="flex items-start gap-4">
              <div class="size-12 rounded-xl bg-on-surface/5 flex items-center justify-center shrink-0 border border-on-surface/10">
                <span class="material-symbols-outlined text-primary" v-if="session.status === 'completed'">check_circle</span>
                <span class="material-symbols-outlined text-secondary" v-else-if="session.status === 'scheduled'">event</span>
                <span class="material-symbols-outlined text-on-surface/50" v-else>cancel</span>
              </div>

              <div>
                <div class="flex items-center gap-2 mb-1">
                  <h4 class="font-bold text-on-surface">{{ formatDate(session.startTime) }}</h4>
                  <span v-if="session.isManualEntry" class="px-2 py-0.5 rounded text-xs uppercase font-bold bg-primary/20 text-primary border border-primary/30">Paper Record</span>
                  <span v-if="session.sessionNumber" class="text-xs text-on-surface/40">#{{ session.sessionNumber }}</span>
                </div>

                <div class="text-sm text-on-surface/60 flex flex-wrap gap-x-4 gap-y-1 items-center">
                  <span class="flex items-center gap-1"><span class="material-symbols-outlined text-[14px]">person</span> {{ getTeacherName(session.teacherId) }}</span>
                  <span class="flex items-center gap-1"><span class="material-symbols-outlined text-[14px]">music_note</span> {{ getInstrumentName(session.instrumentId) }}</span>
                </div>

                <p v-if="session.notes" class="text-sm text-on-surface/80 mt-3 pl-3 border-l-2 border-primary/30 italic">
                  "{{ session.notes }}"
                </p>
              </div>
            </div>

            <div class="flex items-center gap-3">
               <span class="text-xs font-bold uppercase px-3 py-1 rounded-full border"
                 :class="{ 'border-primary/30 text-primary bg-primary/10': session.status === 'completed', 'border-secondary/30 text-secondary bg-secondary/10': session.status === 'scheduled', 'border-on-surface/20 text-on-surface/50': !['completed', 'scheduled'].includes(session.status) }">
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
