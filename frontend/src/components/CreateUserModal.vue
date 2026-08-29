<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue';
import { useUsersStore } from '@stores/users';
import { useRosterStore } from '@stores/roster';
import BaseCard from '@components/BaseCard.vue';
import BaseButton from '@components/BaseButton.vue';
import BaseInput from '@components/BaseInput.vue';
import BaseDropdown from '@components/BaseDropdown.vue';
import type { User, Role, InstrumentRecord } from '@types';

const props = defineProps<{
  isOpen: boolean;
  initialRole?: Role;
}>();

const emit = defineEmits<{
  (e: 'close'): void;
  (e: 'created', user: User): void;
}>();

const usersStore = useUsersStore();
const rosterStore = useRosterStore();

const step = ref<1 | 2>(1);
const selectedRole = ref<Role>('student');

// Form Data
const formData = ref<Partial<User>>({
  name: '',
  email: '',
  role: 'student',
  username: '',
  contactNumber: '',
  homeAddress: '',
  birthday: '',
  age: undefined,
  school: '',
  parentName: '',
  parentContact: '',
  sessionsEnrolled: undefined,
  instruments: []
});
const password = ref('');
const showPassword = ref(false);
const enrollmentCustom = ref(false);

const sessionOptions = [4, 8, 12, 16];

// A student's hours live on an enrollment with a specific teacher, so creating
// the user alone leaves them unable to book anything. Picking a teacher here
// creates that enrollment in the same step.
const enrollTeacherId = ref<number | null>(null);
const teacherOptions = computed(() =>
  usersStore.getUsersByRole('teacher').map((t) => ({ value: t.id, label: t.name })),
);

onMounted(async () => {
  if (usersStore.instruments.length === 0) {
    await usersStore.fetchInstruments();
  }
});

watch(() => props.isOpen, (newVal) => {
  if (newVal) {
    step.value = props.initialRole ? 2 : 1;
    selectedRole.value = props.initialRole || 'student';
    formData.value = {
      name: '', email: '', role: selectedRole.value, username: '',
      contactNumber: '', homeAddress: '', birthday: '', age: undefined,
      school: '', parentName: '', parentContact: '', sessionsEnrolled: undefined, instruments: []
    };
    password.value = '';
    enrollmentCustom.value = false;
    showPassword.value = false;
  }
});

const calculateAge = () => {
  if (formData.value.birthday) {
    const today = new Date();
    const birthDate = new Date(formData.value.birthday);
    let age = today.getFullYear() - birthDate.getFullYear();
    const m = today.getMonth() - birthDate.getMonth();
    if (m < 0 || (m === 0 && today.getDate() < birthDate.getDate())) {
      age--;
    }
    formData.value.age = age;
  }
};

const suggestedUsername = computed(() => {
  if (formData.value.name) {
    const parts = formData.value.name.trim().toLowerCase().split(/\s+/);
    if (parts.length > 1) {
      return `${parts[0]}.${parts[parts.length - 1]}`;
    }
    return parts[0];
  }
  return '';
});

const generatedPassword = computed(() => {
  if (selectedRole.value === 'student' && formData.value.name) {
    const firstName = formData.value.name.split(' ')[0].toLowerCase();
    const ageStr = formData.value.age ? String(formData.value.age) : '';
    return `${firstName}${ageStr}SMC`;
  }
  return '';
});

const toggleInstrument = (inst: InstrumentRecord) => {
  if (!formData.value.instruments) formData.value.instruments = [];
  const index = formData.value.instruments.findIndex(i => i.id === inst.id);
  if (index > -1) {
    formData.value.instruments.splice(index, 1);
  } else {
    formData.value.instruments.push(inst);
  }
};

const isInstrumentSelected = (inst: InstrumentRecord) => {
  return formData.value.instruments?.some(i => i.id === inst.id);
};

const handleNext = () => {
  formData.value.role = selectedRole.value;
  if (!formData.value.username) {
    formData.value.username = suggestedUsername.value;
  }
  step.value = 2;
};

const handleSubmit = async () => {
  try {
    const pwd = selectedRole.value === 'student' && !password.value ? generatedPassword.value : password.value;
    const created = await usersStore.createUser(formData.value, pwd);

    if (selectedRole.value === 'student' && enrollTeacherId.value && created?.id) {
      await rosterStore.createEnrollment({
        studentId: created.id,
        teacherId: enrollTeacherId.value,
        sessionsPurchased: Number(formData.value.sessionsEnrolled) || 0,
      });
    }

    emit('created', created);
    emit('close');
  } catch (err) {
    console.error(err);
  }
};

const copyToClipboard = async (text: string) => {
  try {
    await navigator.clipboard.writeText(text);
  } catch (err) {
    console.error('Failed to copy', err);
  }
};

const closeModal = () => {
  emit('close');
};

const selectStudentRole = () => {
  selectedRole.value = 'student';
};

const selectTeacherRole = () => {
  selectedRole.value = 'teacher';
};

const useSuggestedUsername = () => {
  formData.value.username = suggestedUsername.value;
};

const togglePasswordVisibility = () => {
  showPassword.value = !showPassword.value;
};

const copyGeneratedPassword = () => {
  copyToClipboard(password.value || generatedPassword.value);
};

const setSessionOption = (opt: number) => {
  formData.value.sessionsEnrolled = opt;
  formData.value.sessionsLeft = opt;
  enrollmentCustom.value = false;
};

const enableCustomEnrollment = () => {
  enrollmentCustom.value = true;
};

const handleBackOrClose = () => {
  if (!props.initialRole && step.value === 2) {
    step.value = 1;
  } else {
    closeModal();
  }
};
</script>

<template>
  <div v-if="isOpen" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 dark:bg-black/70">
    <BaseCard class="w-full max-w-2xl max-h-[90vh] overflow-y-auto liquid-glass border border-on-surface/10 p-6 flex flex-col relative">
      <button @click="closeModal" class="absolute top-4 right-4 text-on-surface/50 hover:text-on-surface material-symbols-outlined">close</button>

      <h2 class="text-2xl font-bold text-on-surface mb-6">
        {{ step === 1 ? 'Select Member Role' : `Create New ${selectedRole === 'student' ? 'Student' : 'Teacher'}` }}
      </h2>

      <!-- Step 1: Role Selection -->
      <div v-if="step === 1" class="grid grid-cols-2 gap-4">
        <div
          @click="selectStudentRole"
          class="p-6 rounded-2xl border-2 cursor-pointer transition-all flex flex-col items-center gap-4 text-center"
          :class="selectedRole === 'student' ? 'border-primary bg-primary/10' : 'border-on-surface/10 hover:border-on-surface/30'"
        >
          <span class="material-symbols-outlined text-5xl" :class="selectedRole === 'student' ? 'text-primary' : 'text-on-surface/50'">school</span>
          <div>
            <h3 class="text-xl font-bold text-on-surface">Student</h3>
            <p class="text-sm text-on-surface/50 mt-2">Create a profile for a new student enrolling in classes.</p>
          </div>
        </div>

        <div
          @click="selectTeacherRole"
          class="p-6 rounded-2xl border-2 cursor-pointer transition-all flex flex-col items-center gap-4 text-center"
          :class="selectedRole === 'teacher' ? 'border-primary bg-primary/10' : 'border-on-surface/10 hover:border-on-surface/30'"
        >
          <span class="material-symbols-outlined text-5xl" :class="selectedRole === 'teacher' ? 'text-primary' : 'text-on-surface/50'">music_note</span>
          <div>
            <h3 class="text-xl font-bold text-on-surface">Teacher</h3>
            <p class="text-sm text-on-surface/50 mt-2">Create a profile for a new instructor.</p>
          </div>
        </div>

        <div class="col-span-2 flex justify-end mt-4">
          <BaseButton @click="handleNext">Continue</BaseButton>
        </div>
      </div>

      <!-- Step 2: Form -->
      <form v-else @submit.prevent="handleSubmit" class="space-y-8">
        <!-- Student Form -->
        <template v-if="selectedRole === 'student'">
          <section>
            <h3 class="text-lg font-bold text-on-surface mb-4 flex items-center gap-2">
              <span class="material-symbols-outlined text-primary">person</span> Personal Information
            </h3>
            <div class="grid grid-cols-2 gap-4">
              <BaseInput v-model="formData.name" label="Full Name" required />
              <BaseInput v-model="formData.birthday" label="Birthday" type="date" @change="calculateAge" />
              <BaseInput v-model.number="formData.age" label="Age (Auto-computed)" type="number" readonly />
              <BaseInput v-model="formData.school" label="School" />
              <div class="col-span-2">
                <BaseInput v-model="formData.homeAddress" label="Home Address" />
              </div>
            </div>
          </section>

          <section>
            <h3 class="text-lg font-bold text-on-surface mb-4 flex items-center gap-2">
              <span class="material-symbols-outlined text-primary">shield_person</span> Account
            </h3>
            <div class="grid grid-cols-2 gap-4">
              <div class="relative">
                <BaseInput v-model="formData.username" label="Username" />
                <button v-if="suggestedUsername && !formData.username" type="button" @click="useSuggestedUsername" class="absolute right-2 top-8 text-xs text-primary hover:underline">Use {{ suggestedUsername }}</button>
              </div>
              <BaseInput v-model="formData.email" label="Email Address" type="email" required />
              <div class="col-span-2 relative">
                <BaseInput v-model="password" :label="password ? 'Password' : 'Password (Auto-generated if empty)'" :type="showPassword ? 'text' : 'password'" :placeholder="generatedPassword" />
                <button type="button" @click="togglePasswordVisibility" class="absolute right-10 top-8 text-on-surface/50 hover:text-on-surface material-symbols-outlined text-sm">
                  {{ showPassword ? 'visibility_off' : 'visibility' }}
                </button>
                <button type="button" @click="copyGeneratedPassword" class="absolute right-2 top-8 text-on-surface/50 hover:text-on-surface material-symbols-outlined text-sm" title="Copy password">
                  content_copy
                </button>
                <p v-if="!password && generatedPassword" class="text-xs text-on-surface/40 mt-1">Generated: {{ generatedPassword }}</p>
              </div>
            </div>
          </section>

          <section>
            <h3 class="text-lg font-bold text-on-surface mb-4 flex items-center gap-2">
              <span class="material-symbols-outlined text-primary">family_restroom</span> Parent/Guardian
            </h3>
            <div class="grid grid-cols-2 gap-4">
              <BaseInput v-model="formData.parentName" label="Parent's Name" />
              <BaseInput v-model="formData.parentContact" label="Parent's Contact Number" />
              <div class="col-span-2">
                <BaseInput v-model="formData.contactNumber" label="Student's Contact Number (Optional)" />
              </div>
            </div>
          </section>

          <section>
            <h3 class="text-lg font-bold text-on-surface mb-4 flex items-center gap-2">
              <span class="material-symbols-outlined text-primary">music_cast</span> Enrollment
            </h3>
            <div class="space-y-4">
              <div>
                <BaseDropdown
                  v-model="enrollTeacherId"
                  label="Assign to teacher"
                  placeholder="Select a teacher..."
                  :options="teacherOptions"
                />
                <p class="mt-1 text-xs text-on-surface-variant">
                  Creates the enrollment that lets this student book. Leave empty to add the
                  student without one.
                </p>
              </div>

              <div>
                <label class="block text-sm font-medium text-on-surface/70 mb-2">Lessons (hours)</label>
                <div class="flex flex-wrap gap-2">
                  <button v-for="opt in sessionOptions" :key="opt" type="button"
                    @click="setSessionOption(opt)"
                    class="px-4 py-2 rounded-lg border text-sm transition-colors"
                    :class="formData.sessionsEnrolled === opt && !enrollmentCustom ? 'border-primary bg-primary text-on-primary' : 'border-on-surface/10 text-on-surface/70 hover:border-on-surface/30'">
                    {{ opt }}
                  </button>
                  <button type="button" @click="enableCustomEnrollment" class="px-4 py-2 rounded-lg border text-sm transition-colors" :class="enrollmentCustom ? 'border-primary bg-primary text-on-primary' : 'border-on-surface/10 text-on-surface/70 hover:border-on-surface/30'">Custom</button>
                  <BaseInput v-if="enrollmentCustom" v-model.number="formData.sessionsEnrolled" @input="formData.sessionsLeft = formData.sessionsEnrolled" type="number" class="w-24 ml-2 !mb-0" placeholder="Qty" />
                </div>
              </div>

              <div>
                <label class="block text-sm font-medium text-on-surface/70 mb-2">Instruments</label>
                <div class="flex flex-wrap gap-2">
                  <button v-for="inst in usersStore.instruments" :key="inst.id" type="button"
                    @click="toggleInstrument(inst)"
                    class="px-3 py-1.5 rounded-full text-sm border transition-colors flex items-center gap-1"
                    :class="isInstrumentSelected(inst) ? 'border-primary bg-primary/20 text-primary' : 'border-on-surface/10 text-on-surface/50 hover:border-on-surface/30'">
                    <span v-if="isInstrumentSelected(inst)" class="material-symbols-outlined text-xs">check</span>
                    {{ inst.name }}
                  </button>
                </div>
              </div>
            </div>
          </section>
        </template>

        <!-- Teacher Form -->
        <template v-if="selectedRole === 'teacher'">
           <section>
            <h3 class="text-lg font-bold text-on-surface mb-4 flex items-center gap-2">
              <span class="material-symbols-outlined text-primary">person</span> Personal Information
            </h3>
            <div class="grid grid-cols-2 gap-4">
              <BaseInput v-model="formData.name" label="Full Name" required />
              <BaseInput v-model="formData.contactNumber" label="Contact Number" />
              <div class="col-span-2">
                <BaseInput v-model="formData.homeAddress" label="Home Address" />
              </div>
            </div>
          </section>

          <section>
            <h3 class="text-lg font-bold text-on-surface mb-4 flex items-center gap-2">
              <span class="material-symbols-outlined text-primary">shield_person</span> Account
            </h3>
            <div class="grid grid-cols-2 gap-4">
              <BaseInput v-model="formData.username" label="Username" />
              <BaseInput v-model="formData.email" label="Email Address" type="email" required />
              <div class="col-span-2 relative">
                <BaseInput v-model="password" label="Password" :type="showPassword ? 'text' : 'password'" required />
                <button type="button" @click="togglePasswordVisibility" class="absolute right-2 top-8 text-on-surface/50 hover:text-on-surface material-symbols-outlined text-sm">
                  {{ showPassword ? 'visibility_off' : 'visibility' }}
                </button>
              </div>
            </div>
          </section>

          <section>
            <h3 class="text-lg font-bold text-on-surface mb-4 flex items-center gap-2">
              <span class="material-symbols-outlined text-primary">music_note</span> Teaching
            </h3>
            <div class="space-y-4">
              <div>
                <label class="block text-sm font-medium text-on-surface/70 mb-2">Instruments Taught</label>
                <div class="flex flex-wrap gap-2">
                  <button v-for="inst in usersStore.instruments" :key="inst.id" type="button"
                    @click="toggleInstrument(inst)"
                    class="px-3 py-1.5 rounded-full text-sm border transition-colors flex items-center gap-1"
                    :class="isInstrumentSelected(inst) ? 'border-primary bg-primary/20 text-primary' : 'border-on-surface/10 text-on-surface/50 hover:border-on-surface/30'">
                    <span v-if="isInstrumentSelected(inst)" class="material-symbols-outlined text-xs">check</span>
                    {{ inst.name }}
                  </button>
                </div>
              </div>
              <p class="text-sm text-on-surface/50 italic">Students can be assigned to this teacher later from the Student Records view.</p>
            </div>
          </section>
        </template>

        <div class="flex justify-end gap-4 mt-8 pt-4 border-t border-on-surface/5">
          <BaseButton type="button" variant="secondary" @click="handleBackOrClose">
            {{ !props.initialRole && step === 2 ? 'Back' : 'Cancel' }}
          </BaseButton>
          <BaseButton type="submit" :disabled="usersStore.isLoading">
             <span v-if="usersStore.isLoading" class="material-symbols-outlined animate-spin text-sm mr-2">autorenew</span>
             Create {{ selectedRole === 'student' ? 'Student' : 'Teacher' }}
          </BaseButton>
        </div>
      </form>
    </BaseCard>
  </div>
</template>
