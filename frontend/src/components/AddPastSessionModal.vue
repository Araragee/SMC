<script setup lang="ts">
import { API_URL } from '@typescript/constants'
import { ref, computed, watch } from 'vue';
import { useUsersStore } from '@stores/users';
import BaseCard from '@components/BaseCard.vue';
import BaseButton from '@components/BaseButton.vue';
import BaseInput from '@components/BaseInput.vue';
import type { User } from '@types';
import axios from 'axios';

const props = defineProps<{
  isOpen: boolean;
  student: User;
}>();

const emit = defineEmits<{
  (e: 'close'): void;
  (e: 'created'): void;
}>();

const usersStore = useUsersStore();

const isSubmitting = ref(false);

const formData = ref({
  teacherId: '',
  instrumentId: '',
  date: '',
  startTime: '10:00',
  endTime: '11:00',
  sessionNumber: undefined as number | undefined,
  notes: ''
});

watch(() => props.isOpen, (newVal) => {
  if (newVal) {
    formData.value = {
      teacherId: '',
      instrumentId: '',
      date: new Date().toISOString().split('T')[0],
      startTime: '10:00',
      endTime: '11:00',
      sessionNumber: undefined,
      notes: ''
    };
  }
});

const teachers = computed(() => usersStore.users.filter(u => u.role === 'teacher'));
const studentInstruments = computed(() => props.student.instruments || []);

const handleSubmit = async () => {
  if (!formData.value.teacherId || !formData.value.date) return;

  isSubmitting.value = true;
  try {
    const startDateTime = new Date(`${formData.value.date}T${formData.value.startTime}:00`).toISOString();
    const endDateTime = new Date(`${formData.value.date}T${formData.value.endTime}:00`).toISOString();

    const payload = {
      teacher_id: Number(formData.value.teacherId),
      student_id: Number(props.student.id),
      start_time: startDateTime,
      end_time: endDateTime,
      instrument_id: formData.value.instrumentId ? Number(formData.value.instrumentId) : undefined,
      session_number: formData.value.sessionNumber,
      notes: formData.value.notes
    };

    await axios.post(`${API_URL}/sessions/record`, payload);
    emit('created');
    emit('close');
  } catch (err) {
    console.error("Failed to add past session", err);
  } finally {
    isSubmitting.value = false;
  }
};
</script>

<template>
  <div v-if="isOpen" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
    <BaseCard class="w-full max-w-md max-h-[90vh] overflow-y-auto liquid-glass border border-white/10 p-6 flex flex-col relative">
      <button @click="$emit('close')" class="absolute top-4 right-4 text-white/50 hover:text-white material-symbols-outlined">close</button>

      <h2 class="text-xl font-bold text-white mb-2">Add Past Session</h2>
      <p class="text-sm text-white/50 mb-6">Create a manual record of a completed session for {{ student.name }}.</p>

      <form @submit.prevent="handleSubmit" class="space-y-4">

        <div>
          <label class="block text-sm font-medium text-white/70 mb-1">Teacher</label>
          <select v-model="formData.teacherId" required class="input appearance-none">
            <option value="" disabled>Select a teacher</option>
            <option v-for="t in teachers" :key="t.id" :value="t.id">{{ t.name }}</option>
          </select>
        </div>

        <div>
          <label class="block text-sm font-medium text-white/70 mb-1">Instrument</label>
          <select v-model="formData.instrumentId" class="input appearance-none">
            <option value="">Select an instrument (Optional)</option>
            <option v-for="inst in studentInstruments" :key="inst.id" :value="inst.id">{{ inst.name }}</option>
            <option v-if="studentInstruments.length === 0" disabled value="">No instruments enrolled</option>
          </select>
        </div>

        <div class="grid grid-cols-2 gap-4">
           <div class="col-span-2">
             <BaseInput v-model="formData.date" type="date" label="Date" required />
           </div>
           <BaseInput v-model="formData.startTime" type="time" label="Start Time" required />
           <BaseInput v-model="formData.endTime" type="time" label="End Time" required />
        </div>

        <BaseInput v-model.number="formData.sessionNumber" type="number" label="Session Number (Optional)" placeholder="e.g., 5" />

        <div>
           <label class="block text-sm font-medium text-white/70 mb-1">Notes</label>
           <textarea v-model="formData.notes" rows="3" class="input resize-none"></textarea>
        </div>

        <div class="flex justify-end gap-3 pt-4 border-t border-white/5 mt-6">
          <BaseButton type="button" variant="secondary" @click="$emit('close')">Cancel</BaseButton>
          <BaseButton type="submit" :disabled="isSubmitting">
             <span v-if="isSubmitting" class="material-symbols-outlined animate-spin text-sm mr-2">autorenew</span>
             Save Record
          </BaseButton>
        </div>
      </form>
    </BaseCard>
  </div>
</template>
