import { mount } from '@vue/test-utils'
import { afterEach, describe, expect, it } from 'vitest'
import { nextTick } from 'vue'
import RiskApprovalDialog from '@/components/review/RiskApprovalDialog.vue'

afterEach(() => { document.body.innerHTML = '' })

describe('RiskApprovalDialog', () => {
  it('shows risk context and requires an explicit confirmation', async () => {
    const wrapper = mount(RiskApprovalDialog, {
      attachTo: document.body,
      props: { open: true, issueCount: 3, highestRisk: '高风险' },
    })

    expect(document.body.textContent).toContain('AI 已确认 3 项风险')
    const buttons = document.body.querySelectorAll('button')
    expect(buttons[0].textContent).toContain('取消并继续复核')
    expect(buttons[1].textContent).toContain('确认带风险通过')
    buttons[1].dispatchEvent(new MouseEvent('click', { bubbles: true }))
    await nextTick()
    expect(wrapper.emitted('confirm')).toHaveLength(1)
  })

  it('keeps the confirmation action locked while submitting', () => {
    mount(RiskApprovalDialog, {
      attachTo: document.body,
      props: { open: true, issueCount: 1, highestRisk: '中风险', submitting: true },
    })
    const buttons = [...document.body.querySelectorAll('button')]
    expect(buttons.every(button => button.disabled)).toBe(true)
  })
})
