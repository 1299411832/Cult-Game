import { useEffect, useState } from 'react'
import type { GameSession } from '../types/game'
import { AbandonButton } from './AbandonButton'
import { ChoiceList } from './ChoiceList'
import { EventCard } from './EventCard'
import { EventEditor } from './EventEditor'
import { LogPanel } from './LogPanel'
import { StatusPanel } from './StatusPanel'

interface Props {
  session: GameSession
  onChoose: (choiceId: string) => void
  soundOn: boolean
  onToggleSound: () => void
  onAbandon: () => void
  onUseItem: (index: number) => void
  canRewind: boolean
  onRewind: () => void
}

export function GameScreen({ session, onChoose, soundOn, onToggleSound, onAbandon, onUseItem, canRewind, onRewind }: Props) {
  const { player, currentEvent, turn } = session
  const [showEditor, setShowEditor] = useState(false)

  // Ctrl+Shift+E 打开事件编辑器
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.ctrlKey && e.shiftKey && e.key === 'E') {
        e.preventDefault()
        setShowEditor((v) => !v)
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [])

  if (!currentEvent) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <p className="text-mist tracking-widest">天道渺渺，机缘未至……</p>
      </div>
    )
  }

  return (
    <div className="min-h-screen px-3 py-4 sm:px-5 sm:py-6 md:px-8 md:py-8 max-w-6xl mx-auto relative">
      {/* 顶部工具栏 */}
      <div className="absolute top-3 right-3 sm:top-4 sm:right-4 flex items-center gap-2 sm:gap-3 z-20">
        {canRewind && (
          <button
            type="button"
            onClick={onRewind}
            title="回溯到上一个选择（每局仅限一次）"
            className="text-sm text-gold hover:text-gold-dim transition-colors cursor-pointer
              w-8 h-8 flex items-center justify-center rounded-full border border-gold/30 hover:border-gold/60
              hover:bg-gold/5"
          >
            🔄
          </button>
        )}
        <AbandonButton onAbandon={onAbandon} />
        <button
          type="button"
          onClick={onToggleSound}
          aria-label={soundOn ? '关闭音效' : '开启音效'}
          className="text-sm text-mist hover:text-gold transition-colors cursor-pointer
            w-8 h-8 flex items-center justify-center rounded-full border border-mist/20 hover:border-gold/40"
        >
          {soundOn ? '🔔' : '🔕'}
        </button>
      </div>

      <StatusPanel player={player} turn={turn} onUseItem={onUseItem} />

      <div className="grid lg:grid-cols-[1fr_300px] gap-4 sm:gap-6 lg:gap-7">
        <main className="scroll-panel mist-overlay relative border border-jade/30 bg-ink/65 p-5 sm:p-7 rounded-sm shadow-panel">
          <div className="spirit-motes" aria-hidden="true" />
          <div className="relative z-10">
            <EventCard event={currentEvent} />
            <div className="divider-ornament my-6">
              <span className="ornament-dot" />
            </div>
            <ChoiceList choices={currentEvent.choices} player={player} onChoose={onChoose} />
          </div>
        </main>

        {/* 侧栏不再叠四角描金与云纹，装饰只留给主叙事面板 */}
        <aside className="border border-jade/20 bg-ink/50 p-4 sm:p-5 rounded-sm flex flex-col min-h-0 lg:max-h-[calc(100vh-10rem)] shadow-panel-sm">
          <LogPanel logs={player.log} playerName={player.name} />
        </aside>
      </div>

      {showEditor && (
        <EventEditor
          player={player}
          onClose={() => setShowEditor(false)}
          onChoose={onChoose}
        />
      )}
    </div>
  )
}
