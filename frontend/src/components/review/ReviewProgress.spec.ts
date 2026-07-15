import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import ReviewProgress from '@/components/review/ReviewProgress.vue'

describe('ReviewProgress', () => {
  it('renders real stage states and only animates the running stage', () => {
    const wrapper = mount(ReviewProgress, {
      props: {
        stages: [
          { key: 'accepted', label: '物料已接收', status: 'completed' },
          { key: 'legal_review', label: '法规审核', status: 'completed' },
          { key: 'public_opinion_review', label: '舆情审核', status: 'running' },
          { key: 'finalizing', label: '汇总审查结果', status: 'pending' },
        ],
      },
    })

    expect(wrapper.text()).toContain('舆情审核')
    expect(wrapper.findAll('.review-progress-marker.is-running')).toHaveLength(1)
    expect(wrapper.find('[data-status="running"]').text()).toContain('进行中')
  })
})
