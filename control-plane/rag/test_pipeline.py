"""Phase 2a pipeline test — run inside WSL or container."""
import sys
import os

# Test contract text
PAGES = [
    "销售合同\n\n"
    "第一条 合同标的\n"
    "甲方同意出售、乙方同意购买以下产品。\n"
    "产品名称：工业设备X-2000\n"
    "数量：100台\n\n"
    "第二条 价格与支付\n"
    "合同总金额为人民币500万元整。\n"
    "乙方应于合同签订后15日内支付30%定金。\n"
    "余款应在交货前5个工作日内付清。\n\n"
    "第三条 交货\n"
    "甲方应于收到定金后30日内完成交货。\n"
    "交货地点为乙方指定仓库。\n"
    "运输费用由甲方承担。\n\n"
    "第四条 验收\n"
    "乙方应在收到货物后7个工作日内完成验收。\n"
    "如有质量问题，应在验收期内书面通知甲方。\n\n"
    "第五条 违约责任\n"
    "任何一方违约，应向对方支付合同总金额20%的违约金。\n"
    "因不可抗力导致的延迟不视为违约。\n\n"
    "第六条 保密条款\n"
    "双方应对本合同内容保密，不得向第三方披露。\n"
    "保密义务在本合同终止后三年内继续有效。\n\n"
    "第七条 争议解决\n"
    "本合同适用中华人民共和国法律。\n"
    "如发生争议，应提交北京仲裁委员会仲裁。\n"
    "仲裁裁决是终局的，对双方均有约束力。\n\n"
    "第八条 其他\n"
    "本合同一式两份，双方各执一份。\n"
    "本合同自双方签字盖章之日起生效。\n",
]

if __name__ == "__main__":
    # Test chunker
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from rag.chunker import chunk_text, count_tokens

    chunks = chunk_text(PAGES)
    print(f"Chunks: {len(chunks)}")
    for c in chunks:
        print(f"  [{c['chunk_index']}] page={c['page_num']} "
              f"tokens={c['tokens']} text={c['content'][:60]}...")
    print(f"\nTotal tokens: {sum(c['tokens'] for c in chunks)}")
