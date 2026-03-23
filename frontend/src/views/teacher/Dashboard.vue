<template>
  <div class="flex-1 w-full min-h-screen pt-6 pb-20 relative flex">
    <!-- Content Columns -->
      <div class="w-full max-w-[1400px] mx-auto mt-28 flex gap-8">
        
        <!-- Left Section (Welcome, Roster, Stats) -->
        <div class="flex-1 space-y-8 max-w-[700px]">
          
          <!-- Header Intro -->
          <div class="flex items-end justify-between">
            <div>
              <h2 class="text-5xl font-black tracking-tight mb-2">
                Welcome back, <span class="text-[#f94d00]">Maestro.</span>
              </h2>
              <p class="text-zinc-400 text-base">
                You have <span class="font-bold text-white">{{ todaySessions.length || 4 }} sessions</span> today. Performance index is at <span class="text-emerald-500 font-bold">98%</span>.
              </p>
            </div>
            <!-- Next Up Pill -->
            <div v-if="nextSession" class="flex items-center gap-4 bg-[#1a1a1a]/80 border border-white/5 rounded-full pl-2 pr-6 py-2 shadow-2xl">
              <div class="w-10 h-10 rounded-full bg-gradient-to-br from-orange-600 to-red-600 flex items-center justify-center shrink-0">
                <span class="material-symbols-outlined text-white text-sm" style="font-variation-settings:'FILL' 1">schedule</span>
              </div>
              <div>
                <p class="text-[9px] uppercase tracking-widest text-zinc-500 font-bold">Next Up</p>
                <p class="text-sm font-black text-white">{{ formatTime(nextSession.startTime) }} • Drum Session</p>
              </div>
            </div>
            <div v-else class="flex items-center gap-4 bg-[#1a1a1a]/80 border border-white/5 rounded-full pl-2 pr-6 py-2 shadow-2xl">
              <div class="w-10 h-10 rounded-full bg-gradient-to-br from-orange-600 to-red-600 flex items-center justify-center shrink-0">
                <span class="material-symbols-outlined text-white text-sm" style="font-variation-settings:'FILL' 1">schedule</span>
              </div>
              <div>
                <p class="text-[9px] uppercase tracking-widest text-zinc-500 font-bold">Next Up</p>
                <p class="text-sm font-black text-white">14:00 • Rock Drums</p>
              </div>
            </div>
          </div>

          <!-- Student Roster -->
          <div class="bg-[#1a1919]/60 backdrop-blur-xl border border-white/5 rounded-[2rem] p-8 pb-10 shadow-2xl shadow-black/50 relative overflow-hidden">
            <div class="flex items-center justify-between mb-8 z-10 relative">
              <div class="flex items-center gap-3">
                <span class="material-symbols-outlined text-[#ff6b35] text-[28px]" style="font-variation-settings:'FILL' 1">group</span>
                <h3 class="text-2xl font-bold text-white">Student Roster</h3>
              </div>
              <button class="text-[#ff6b35] text-xs font-bold uppercase tracking-widest hover:text-white transition-colors">
                View All Roster
              </button>
            </div>
            
            <div class="grid grid-cols-2 gap-4 relative z-10">
              <div class="bg-[#111111]/80 rounded-[1.5rem] p-5 flex items-center gap-4 border border-white/5 hover:border-white/10 transition-all cursor-pointer group shadow-xl">
                <img src="https://i.pravatar.cc/150?img=47" alt="Elena Rodriguez" class="w-14 h-14 rounded-full border-2 border-orange-500 shrink-0 object-cover" />
                <div class="flex-1 min-w-0">
                  <h4 class="font-bold text-white text-base truncate">Elena<br/>Rodriguez</h4>
                  <p class="text-[10px] text-zinc-500 uppercase tracking-widest mt-0.5">Piano • Level 7</p>
                  <div class="flex items-center gap-2 mt-2">
                    <span class="text-[10px] font-bold bg-[#1e1e1e] text-zinc-300 px-2.5 py-1 rounded-full border border-white/5">MON 4PM</span>
                    <span class="text-[9px] font-bold text-[#f94d00] uppercase border border-[#f94d00]/30 rounded-full px-2 py-1 bg-[#f94d00]/10">Progress: High</span>
                  </div>
                </div>
                <span class="material-symbols-outlined text-zinc-600 group-hover:text-white transition-colors">chevron_right</span>
              </div>
              
              <div class="bg-[#111111]/80 rounded-[1.5rem] p-5 flex items-center gap-4 border border-white/5 hover:border-white/10 transition-all cursor-pointer group shadow-xl">
                <img src="https://i.pravatar.cc/150?img=11" alt="Julian Chen" class="w-14 h-14 rounded-full border-2 border-[#1a1a1a] shadow-[0_0_0_2px_#3b82f6] shrink-0 object-cover" />
                <div class="flex-1 min-w-0">
                  <h4 class="font-bold text-white text-base truncate">Julian Chen</h4>
                  <p class="text-[10px] text-zinc-500 uppercase tracking-widest mt-0.5">Drums • Advanced</p>
                  <div class="flex items-center gap-2 mt-2">
                    <span class="text-[10px] font-bold bg-[#1e1e1e] text-zinc-300 px-2.5 py-1 rounded-full border border-white/5">TUE 2PM</span>
                    <span class="text-[9px] font-bold text-zinc-400 uppercase border border-zinc-700 rounded-full px-2 py-1 bg-zinc-800">Practice: Mid</span>
                  </div>
                </div>
                <span class="material-symbols-outlined text-zinc-600 group-hover:text-white transition-colors">chevron_right</span>
              </div>
            </div>
            
            <button class="mt-6 w-1/2 border-2 border-dashed border-white/10 rounded-[1.5rem] p-6 flex flex-col items-center justify-center gap-2 hover:bg-white/5 hover:border-white/20 transition-all text-zinc-500 mx-auto">
              <span class="material-symbols-outlined text-3xl" style="font-variation-settings:'FILL' 1">person_add</span>
              <span class="text-[10px] font-bold uppercase tracking-widest">Enroll New</span>
            </button>
          </div>

          <!-- Weekly Schedule Card -->
          <div class="bg-[#1a1919]/60 backdrop-blur-xl border border-white/5 rounded-[2rem] p-8 shadow-2xl relative">
            <div class="flex items-center justify-between mb-8">
              <div class="flex items-center gap-3">
                <span class="material-symbols-outlined text-[#ff6b35] text-[28px]" style="font-variation-settings:'FILL' 1">event</span>
                <h3 class="text-2xl font-bold text-white">Weekly Schedule</h3>
              </div>
              <div class="flex gap-2">
                <button class="w-10 h-10 rounded-full bg-[#2a2a2a] text-zinc-400 flex items-center justify-center hover:text-white hover:bg-[#333] transition-all">
                  <span class="material-symbols-outlined text-sm">chevron_left</span>
                </button>
                <button class="w-10 h-10 rounded-full bg-[#2a2a2a] text-zinc-400 flex items-center justify-center hover:text-white hover:bg-[#333] transition-all">
                  <span class="material-symbols-outlined text-sm">chevron_right</span>
                </button>
              </div>
            </div>

            <div class="grid grid-cols-5 gap-3">
              <!-- Monday -->
              <div class="flex flex-col gap-3">
                <p class="text-[10px] text-zinc-500 uppercase font-bold tracking-[0.2em] text-center">Mon</p>
                <div class="bg-transparent border border-[#ff6b35] rounded-[1.5rem] p-4 text-center cursor-pointer shadow-[inset_0_0_20px_rgba(255,107,53,0.1)]">
                  <p class="text-xs text-[#ff6b35] font-black">16:00</p>
                  <p class="text-sm font-bold text-white mt-1">Elena R.</p>
                  <p class="text-[10px] text-zinc-500">Piano II</p>
                </div>
              </div>
              <!-- Tuesday -->
              <div class="flex flex-col gap-3">
                <p class="text-[10px] text-zinc-500 uppercase font-bold tracking-[0.2em] text-center">Tue</p>
                <div class="bg-transparent border border-orange-400 rounded-[1.5rem] p-4 text-center cursor-pointer shadow-[inset_0_0_20px_rgba(249,115,22,0.1)]">
                  <p class="text-xs text-orange-400 font-black">14:00</p>
                  <p class="text-sm font-bold text-white mt-1">Julian C.</p>
                  <p class="text-[10px] text-zinc-500">Rock Drums</p>
                </div>
              </div>
              <!-- Wednesday -->
              <div class="flex flex-col gap-3">
                <p class="text-[10px] text-zinc-500 uppercase font-bold tracking-[0.2em] text-center">Wed</p>
                <div class="bg-[#111111] border border-dashed border-white/5 rounded-[1.5rem] h-full min-h-[100px] flex items-center justify-center cursor-pointer hover:bg-white/5 transition-colors">
                  <span class="material-symbols-outlined text-zinc-600">add</span>
                </div>
              </div>
              <!-- Thursday -->
              <div class="flex flex-col gap-3">
                <p class="text-[10px] text-zinc-500 uppercase font-bold tracking-[0.2em] text-center">Thu</p>
                <div class="bg-[#1e1e1e] border border-white/5 rounded-[1.5rem] p-4 text-center cursor-pointer hover:bg-[#262626] transition-colors">
                  <p class="text-xs text-zinc-400 font-bold">17:00</p>
                  <p class="text-sm font-bold text-white mt-1">Sarah M.</p>
                  <p class="text-[10px] text-zinc-500">Vocals</p>
                </div>
              </div>
              <!-- Friday -->
              <div class="flex flex-col gap-3">
                <p class="text-[10px] text-zinc-500 uppercase font-bold tracking-[0.2em] text-center">Fri</p>
                <div class="bg-[#111111] border border-dashed border-white/5 rounded-[1.5rem] h-full flex items-center justify-center cursor-pointer hover:bg-white/5 transition-colors">
                  <span class="material-symbols-outlined text-zinc-600">add</span>
                </div>
              </div>
            </div>
          </div>

          <!-- Bottom Row: 3 KPI Cards -->
          <div class="grid grid-cols-3 gap-6">
            <div class="bg-[#1a1919]/60 backdrop-blur-xl border border-white/5 rounded-[2rem] p-6 shadow-2xl flex items-center gap-4">
              <div class="w-16 h-16 rounded-2xl bg-[#f94d00] flex items-center justify-center text-white text-3xl font-black">12</div>
              <div>
                <p class="text-base font-bold text-white">Active Roster</p>
                <p class="text-[11px] text-zinc-500 leading-tight mt-1">Enrolled for Summer<br/>Term</p>
              </div>
            </div>
            <div class="bg-[#1a1919]/60 backdrop-blur-xl border border-white/5 rounded-[2rem] p-6 shadow-2xl flex items-center gap-4">
              <div class="w-16 h-16 rounded-2xl bg-[#71401b] flex items-center justify-center text-[#ff6b35]">
                <span class="material-symbols-outlined text-3xl" style="font-variation-settings:'FILL' 1">star</span>
              </div>
              <div>
                <p class="text-base font-bold text-white">Rating: 4.98</p>
                <p class="text-[11px] text-zinc-500 leading-tight mt-1">Based on 142<br/>reviews</p>
              </div>
            </div>
            <div class="bg-[#1a1919]/60 backdrop-blur-xl border border-white/5 rounded-[2rem] p-6 shadow-2xl flex items-center gap-4">
              <div class="w-16 h-16 rounded-2xl bg-[#0b3323] flex items-center justify-center text-emerald-400">
                <span class="material-symbols-outlined text-3xl" style="font-variation-settings:'FILL' 1">leaderboard</span>
              </div>
              <div>
                <p class="text-base font-bold text-white">Growth Hub</p>
                <p class="text-[11px] text-zinc-500 leading-tight mt-1">+15% Month-over-<br/>Month</p>
              </div>
            </div>
          </div>

        </div>

        <!-- Right Section (Live Session Highlight Card) -->
        <div class="w-[380px] shrink-0">
          <div class="bg-[#111111] overflow-hidden rounded-[2.5rem] border border-white/5 shadow-2xl flex flex-col h-[850px] relative">
            <!-- Distinct Top Gradient Block -->
            <div class="bg-gradient-to-br from-[#ff6b35] to-[#d43700] p-8 pt-10 relative">
              <div class="flex justify-between items-start mb-6">
                <span class="text-[9px] uppercase tracking-[0.2em] font-bold border border-white/30 rounded-full px-3 py-1 text-white">Live Session</span>
                <button class="text-white hover:text-white/80 active:scale-95 transition-all">
                  <span class="material-symbols-outlined">more_horiz</span>
                </button>
              </div>
              <h3 class="text-[28px] font-black text-white leading-tight mb-2 tracking-tight">Julian Chen:<br/>Advanced Rock<br/>Drumming</h3>
              <p class="text-xs font-bold text-white/80 tracking-widest uppercase">ID: #4429 • Room 104 • 14:00</p>
            </div>
            
            <!-- Darker Body -->
            <div class="p-8 pt-6 flex flex-col flex-1 bg-[#151515]">
              <div class="mb-10">
                <p class="text-[10px] text-zinc-500 uppercase tracking-widest font-bold mb-4">Visual Evidence</p>
                <div class="border-2 border-dashed border-white/10 rounded-[2rem] h-32 flex flex-col items-center justify-center cursor-pointer hover:border-[#ff6b35]/50 transition-colors bg-[#0e0e0e]/50">
                  <div class="w-12 h-12 rounded-full bg-[#3d180b] flex items-center justify-center mb-2">
                    <span class="material-symbols-outlined text-[#ff6b35]" style="font-variation-settings:'FILL' 1">photo_camera</span>
                  </div>
                  <span class="text-xs font-bold text-white">Take Photo or Upload</span>
                </div>
              </div>

              <div>
                <p class="text-[10px] text-zinc-500 uppercase tracking-widest font-bold mb-4">Next Week's Practice Goals</p>
                <div class="bg-[#0e0e0e]/80 rounded-[2rem] p-6 h-32 border border-white/5 flex items-start">
                  <p class="text-sm text-zinc-500 w-full outline-none">E.g. Focus on paradiddle transitions at 120bpm...</p>
                </div>
              </div>

              <div class="mt-8 mb-auto">
                <p class="text-[10px] text-zinc-500 uppercase tracking-widest font-bold mb-4">Shared Resources</p>
                <div class="bg-[#0e0e0e]/80 rounded-2xl p-4 flex items-center gap-4 border border-white/5 hover:border-white/10 transition-colors py-3">
                  <div class="w-10 h-10 rounded-xl bg-[#2b1406] flex items-center justify-center shrink-0">
                    <span class="material-symbols-outlined text-[#ff6b35]" style="font-variation-settings:'FILL' 1">music_note</span>
                  </div>
                  <div class="flex-1 min-w-0">
                    <p class="text-xs font-bold text-white truncate">Drum_Fills_Intermediate.pdf</p>
                    <p class="text-[9px] text-zinc-500 uppercase tracking-widest mt-0.5">1.2 MB • Sheet Music</p>
                  </div>
                  <span class="material-symbols-outlined text-zinc-500 hover:text-white cursor-pointer transition-colors text-sm">close</span>
                </div>
              </div>

              <button class="w-full bg-gradient-to-r from-[#ff3800] to-[#ff5d00] text-white rounded-full py-5 text-sm font-black tracking-widest shadow-[0_4px_30px_rgba(255,56,0,0.5)] mt-4 hover:scale-[1.02] active:scale-95 transition-all">
                COMPLETE SESSION
              </button>
            </div>

          </div>
        </div>

      </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useAuthStore } from '../../stores/auth'
import { useScheduleStore } from '../../stores/schedule'

const authStore = useAuthStore()
const scheduleStore = useScheduleStore()

const mySessions = computed(() => scheduleStore.allSessions.filter(s => s.teacherId === authStore.currentUser?.id))
const todaySessions = computed(() => mySessions.value.filter(s => new Date(s.startTime).toDateString() === new Date().toDateString()))
const nextSession = computed(() => todaySessions.value[0])

const formatTime = (iso?: string) => iso ? new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: false }) : '14:00'
</script>
