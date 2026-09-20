import openpyxl
def cost_sub(path):
    p=path.split('>')
    a='>'.join(p[:2])
    if a=='식품>음료': return '음료·커피'
    if a in ('식품>스낵/과자','식품>젤리/사탕/초콜릿','식품>아이스크림/빙수'): return '과자·간식'
    if a in ('식품>농산물','식품>수산물','식품>축산물','식품>냉동/간편조리식품','식품>유가공품'): return '신선·냉동식품'
    if p[0]=='식품': return '소스·오일·양념'
    if a=='생활/건강>반려동물': return '반려동물'
    if p[0]=='화장품/미용': return '뷰티·바디'
    if p[0] in ('스포츠/레저','패션잡화','패션의류'): return '스포츠·잡화'
    return '주방·생활·가전'
def misc_sub(path):
    t=path.split('>')[0]
    return {'패션잡화':'패션잡화','패션의류':'패션잡화','생활/건강':'생활·건강용품','화장품/미용':'뷰티','디지털/가전':'디지털·가전','가구/인테리어':'가구·인테리어'}.get(t,'기타')
def load():
    ws=openpyxl.load_workbook('/Users/haengboghanna/Desktop/코스트코스마트스토어클로드/스토어_상품분류표.xlsx')['상품분류']
    out={'코스트코관':{},'생활잡화':{}}
    for r in ws.iter_rows(min_row=2,values_only=True):
        pid,name,price,path,src,menu,sub=r[:7]
        pid=str(pid)
        if menu=='코스트코관': out['코스트코관'].setdefault(cost_sub(path),[]).append(pid)
        elif menu=='생활·잡화': out['생활잡화'].setdefault(misc_sub(path),[]).append(pid)
    return out
if __name__=='__main__':
    d=load()
    for k,v in d.items():
        print(k,sum(len(x) for x in v.values()),{a:len(b) for a,b in v.items()})
