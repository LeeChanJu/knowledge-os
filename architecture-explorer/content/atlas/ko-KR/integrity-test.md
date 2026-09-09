저장된 메타데이터와 해시가 맞는지, 같은 리비전에 다른 URI를 넣으면 거절하는지 실제 Neo4j 회귀로 검사합니다. 테스트 파일은 실행 결과와 구별됩니다.

<!-- DEPTH -->

### 왜 이 책임이 필요한가

Preserve the accepted verification scope and its dependency coverage without turning it into a subsystem-wide claim.

### 입력과 출력

입력: 명시된 입력 범위 없음. 연결된 계약에서 확인합니다.

출력: 명시된 출력 범위 없음.

### 무엇을 보존하는가

- Documentation of the claim; no runtime data.
- Verification applies only to the declared scope and pinned dependencies.

### 예시를 따라가 보기

메모의 제공자가 바뀌어도 원본 식별·근거·승인 경계를 다시 정의하지 않습니다. 실제 부족함이 측정될 때 계약과 설계 변경을 검토합니다.

### 혼동하지 말아야 할 점

Verification applies only to the declared scope and pinned dependencies.
