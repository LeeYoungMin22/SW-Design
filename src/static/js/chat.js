// static/js/chat.js
// 채팅 인터페이스 관리 JavaScript

/**
 * 채팅 관리자 - 채팅 UI와 메시지 처리를 담당
 */
window.ChatManager = {
	// DOM 요소들
	elements: {
			chatMessages: null,
			chatInput: null,
			sendBtn: null,
			loadingIndicator: null,
			exampleQuestions: null,
			sideMenu: null,
			overlay: null,
			menuBtn: null,
			closeMenuBtn: null
	},
	
	// 상태 관리
	state: {
			isWaitingResponse: false,
			currentSessionId: null,
			messageHistory: [],
			lastMessageTime: null
	},
	
	// 초기화
	init() {
			this.bindElements();
			this.setupEventListeners();
			this.generateSessionId();
			this.loadChatHistory();
			this.setupAutoScroll();
			console.log('채팅 관리자가 초기화되었습니다.');
	},
	
	// DOM 요소 바인딩
	bindElements() {
			this.elements.chatMessages = DOM.$('#chatMessages');
			this.elements.chatInput = DOM.$('#chatInput');
			this.elements.sendBtn = DOM.$('#sendBtn');
			this.elements.loadingIndicator = DOM.$('#loadingIndicator');
			this.elements.exampleQuestions = DOM.$('#exampleQuestions');
			this.elements.sideMenu = DOM.$('#sideMenu');
			this.elements.overlay = DOM.$('#overlay');
			this.elements.menuBtn = DOM.$('#menuBtn');
			this.elements.closeMenuBtn = DOM.$('#closeMenuBtn');
	},
	
	// 이벤트 리스너 설정
	setupEventListeners() {
			// 메시지 전송
			this.elements.sendBtn?.addEventListener('click', () => this.handleSendMessage());
			
			// 엔터키로 메시지 전송
			this.elements.chatInput?.addEventListener('keydown', (e) => {
					if (e.key === 'Enter' && !e.shiftKey) {
							e.preventDefault();
							this.handleSendMessage();
					}
			});
			
			// 입력 필드 실시간 검증
			this.elements.chatInput?.addEventListener('input', (e) => {
					this.handleInputChange(e.target.value);
			});
			
			// 예제 질문 클릭
			this.elements.exampleQuestions?.addEventListener('click', (e) => {
					const card = e.target.closest('.example-card');
					if (card) {
							const question = card.dataset.question;
							this.handleExampleQuestion(question);
					}
			});
			
			// 사이드 메뉴 토글
			this.elements.menuBtn?.addEventListener('click', () => this.toggleSideMenu());
			this.elements.closeMenuBtn?.addEventListener('click', () => this.closeSideMenu());
			this.elements.overlay?.addEventListener('click', () => this.closeSideMenu());
			
			// 대화 내용 지우기
			DOM.$('#clearChatBtn')?.addEventListener('click', () => this.clearChat());
			
			// 식당 카드 클릭 이벤트 (동적으로 추가되는 요소)
			this.elements.chatMessages?.addEventListener('click', (e) => {
					const restaurantCard = e.target.closest('.restaurant-card');
					if (restaurantCard) {
							this.handleRestaurantCardClick(restaurantCard);
					}
			});
	},
	
	// 세션 ID 생성
	generateSessionId() {
			this.state.currentSessionId = 'chat_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
	},
	
	// 메시지 전송 처리
	async handleSendMessage() {
			const message = this.elements.chatInput.value.trim();
			if (!message || this.state.isWaitingResponse) return;
			
			try {
					// 사용자 메시지 표시
					this.addUserMessage(message);
					this.clearInput();
					this.hideExampleQuestions();
					this.showLoading();
					
					this.state.isWaitingResponse = true;
					
					// API 요청
					const response = await APIClient.post('/chat/message', {
							message: message,
							session_id: this.state.currentSessionId,
							timestamp: new Date().toISOString()
					});
					
					if (response.success) {
							this.addBotResponse(response.data);
					} else {
							throw new Error(response.error || '응답을 받을 수 없습니다.');
					}
					
			} catch (error) {
					console.error('메시지 전송 오류:', error);
					this.addErrorMessage('죄송합니다. 서버에 일시적인 문제가 발생했습니다. 잠시 후 다시 시도해주세요.');
					FOODI.showNotification('메시지 전송에 실패했습니다.', 'error');
			} finally {
					this.hideLoading();
					this.state.isWaitingResponse = false;
					this.updateSendButtonState();
			}
	},
	
	// 입력 변경 처리
	handleInputChange(value) {
			this.updateSendButtonState();
			
			// 입력 제안 기능 (향후 구현)
			if (value.length > 2) {
					this.showInputSuggestions(value);
			} else {
					this.hideInputSuggestions();
			}
	},
	
	// 예제 질문 처리
	handleExampleQuestion(question) {
			this.elements.chatInput.value = question;
			this.handleSendMessage();
	},
	
	// 사용자 메시지 추가
	addUserMessage(message) {
			const messageElement = this.createMessageElement('user', message);
			this.appendMessage(messageElement);
			this.saveMessageToHistory('user', message);
	},
	
	// 봇 응답 추가
	addBotResponse(responseData) {
			const messageElement = this.createBotResponseElement(responseData);
			this.appendMessage(messageElement);
			this.saveMessageToHistory('bot', responseData);
	},
	
	// 에러 메시지 추가
	addErrorMessage(message) {
			const messageElement = this.createMessageElement('bot', message, 'error');
			this.appendMessage(messageElement);
	},
	
	// 메시지 요소 생성
	createMessageElement(type, content, messageType = 'normal') {
			const messageDiv = DOM.create('div', { className: `message ${type}-message` });
			
			// 아바타
			const avatar = DOM.create('div', { className: 'message-avatar' });
			avatar.innerHTML = type === 'user' ? '<i class="fas fa-user"></i>' : '<i class="fas fa-robot"></i>';
			
			// 메시지 내용
			const messageContent = DOM.create('div', { className: 'message-content' });
			const messageText = DOM.create('div', { 
					className: `message-text ${messageType === 'error' ? 'error-message' : ''}` 
			});
			messageText.innerHTML = this.formatMessageContent(content);
			
			const messageTime = DOM.create('div', { className: 'message-time' });
			messageTime.textContent = Utils.formatDate(new Date(), 'HH:mm');
			
			messageContent.appendChild(messageText);
			messageContent.appendChild(messageTime);
			
			messageDiv.appendChild(avatar);
			messageDiv.appendChild(messageContent);
			
			return messageDiv;
	},
	
	// 봇 응답 요소 생성 (식당 추천 포함)
	createBotResponseElement(responseData) {
			const messageDiv = this.createMessageElement('bot', responseData.message || responseData.text);
			
			// 식당 추천이 있는 경우 추가
			if (responseData.restaurants && responseData.restaurants.length > 0) {
					const recommendationsDiv = DOM.create('div', { className: 'restaurant-recommendations' });
					
					responseData.restaurants.forEach(restaurant => {
							const restaurantCard = this.createRestaurantCard(restaurant);
							recommendationsDiv.appendChild(restaurantCard);
					});
					
					messageDiv.querySelector('.message-content').appendChild(recommendationsDiv);
			}
			
			return messageDiv;
	},
	
	// 식당 카드 생성
	createRestaurantCard(restaurant) {
			const card = DOM.create('div', { 
					className: 'restaurant-card',
					'data-restaurant-id': restaurant.id 
			});
			
			card.innerHTML = `
					<div class="restaurant-header">
							<h4 class="restaurant-name">${restaurant.name}</h4>
							<div class="restaurant-rating">
									<i class="fas fa-star"></i>
									<span>${restaurant.rating || '0.0'}</span>
							</div>
					</div>
					<div class="restaurant-info">
							<div class="info-item">
									<i class="fas fa-utensils"></i>
									<span>${restaurant.category || '기타'}</span>
							</div>
							<div class="info-item">
									<i class="fas fa-won-sign"></i>
									<span>${restaurant.price_range || '정보 없음'}</span>
							</div>
							<div class="info-item">
									<i class="fas fa-clock"></i>
									<span>${restaurant.hours || '정보 없음'}</span>
							</div>
							<div class="info-item">
									<i class="fas fa-map-marker-alt"></i>
									<span>${restaurant.district || '대구 달서구'}</span>
							</div>
					</div>
					<div class="restaurant-description">
							${restaurant.description || restaurant.summary || '맛있는 음식을 제공하는 식당입니다.'}
					</div>
					<div class="restaurant-actions">
							<button class="btn btn-outline btn-sm view-details-btn">
									<i class="fas fa-info-circle"></i>
									상세 보기
							</button>
							<button class="btn btn-primary btn-sm view-map-btn">
									<i class="fas fa-map-marker-alt"></i>
									지도 보기
							</button>
					</div>
			`;
			
			return card;
	},
	
	// 메시지 내용 포맷팅
	formatMessageContent(content) {
			if (typeof content === 'string') {
					// 링크 변환
					content = content.replace(
							/(https?:\/\/[^\s]+)/g, 
							'<a href="$1" target="_blank" rel="noopener">$1</a>'
					);
					
					// 줄바꿈 변환
					content = content.replace(/\n/g, '<br>');
			}
			
			return content;
	},
	
	// 메시지 추가 및 스크롤
	appendMessage(messageElement) {
			this.elements.chatMessages.appendChild(messageElement);
			this.scrollToBottom();
	},
	
	// 하단으로 스크롤
	scrollToBottom() {
			requestAnimationFrame(() => {
					this.elements.chatMessages.scrollTop = this.elements.chatMessages.scrollHeight;
			});
	},
	
	// 자동 스크롤 설정
	setupAutoScroll() {
			// 새 메시지가 추가될 때 자동으로 스크롤
			const observer = new MutationObserver(() => {
					if (this.isScrolledToBottom()) {
							this.scrollToBottom();
					}
			});
			
			observer.observe(this.elements.chatMessages, {
					childList: true,
					subtree: true
			});
	},
	
	// 하단에 스크롤되어 있는지 확인
	isScrolledToBottom() {
			const { scrollTop, scrollHeight, clientHeight } = this.elements.chatMessages;
			return scrollTop + clientHeight >= scrollHeight - 10;
	},
	
	// 전송 버튼 상태 업데이트
	updateSendButtonState() {
			const hasText = this.elements.chatInput.value.trim().length > 0;
			const isEnabled = hasText && !this.state.isWaitingResponse;
			
			if (isEnabled) {
					DOM.enable(this.elements.sendBtn);
			} else {
					DOM.disable(this.elements.sendBtn);
			}
	},
	
	// 입력 필드 클리어
	clearInput() {
			this.elements.chatInput.value = '';
			this.updateSendButtonState();
	},
	
	// 로딩 표시
	showLoading() {
			DOM.show(this.elements.loadingIndicator);
	},
	
	// 로딩 숨김
	hideLoading() {
			DOM.hide(this.elements.loadingIndicator);
	},
	
	// 예제 질문 숨김
	hideExampleQuestions() {
			if (this.elements.exampleQuestions) {
					DOM.hide(this.elements.exampleQuestions);
			}
	},
	
	// 사이드 메뉴 토글
	toggleSideMenu() {
			DOM.toggleClass(this.elements.sideMenu, 'active');
			DOM.toggleClass(this.elements.overlay, 'active');
	},
	
	// 사이드 메뉴 닫기
	closeSideMenu() {
			this.elements.sideMenu?.classList.remove('active');
			this.elements.overlay?.classList.remove('active');
	},
	
	// 대화 내용 지우기
	clearChat() {
			if (confirm('대화 내용을 모두 지우시겠습니까?')) {
					this.elements.chatMessages.innerHTML = '';
					this.state.messageHistory = [];
					this.generateSessionId();
					
					// 웰컴 메시지 다시 표시
					this.addBotResponse({
							message: '안녕하세요! 새로운 대화를 시작합니다. 어떤 음식이 드시고 싶으신지 말씀해주세요. 🍽️'
					});
					
					// 예제 질문 다시 표시
					if (this.elements.exampleQuestions) {
							DOM.show(this.elements.exampleQuestions);
					}
					
					this.closeSideMenu();
					FOODI.showNotification('대화 내용이 지워졌습니다.', 'success');
			}
	},
	
	// 식당 카드 클릭 처리
	handleRestaurantCardClick(card) {
			const restaurantId = card.dataset.restaurantId;
			const button = event.target.closest('button');
			
			if (button?.classList.contains('view-details-btn')) {
					this.showRestaurantDetails(restaurantId);
			} else if (button?.classList.contains('view-map-btn')) {
					this.showRestaurantOnMap(restaurantId);
			}
	},
	
	// 식당 상세 정보 표시
	async showRestaurantDetails(restaurantId) {
			try {
					const response = await APIClient.get(`/restaurants/${restaurantId}`);
					if (response.success) {
							// 모달 표시 로직 (모달 컴포넌트 필요)
							if (window.RestaurantModal) {
									RestaurantModal.show(response.data.restaurant);
							}
					}
			} catch (error) {
					console.error('식당 정보 로드 실패:', error);
					FOODI.showNotification('식당 정보를 불러올 수 없습니다.', 'error');
			}
	},
	
	// 지도에서 식당 위치 표시
	showRestaurantOnMap(restaurantId) {
			if (window.MapManager) {
					MapManager.showRestaurantLocation(restaurantId);
			}
	},
	
	// 메시지 히스토리 저장
	saveMessageToHistory(type, content) {
			const messageData = {
					type,
					content,
					timestamp: new Date().toISOString()
			};
			
			this.state.messageHistory.push(messageData);
			this.state.lastMessageTime = messageData.timestamp;
			
			// 세션에 저장
			Utils.session.set('chatHistory', this.state.messageHistory);
	},
	
	// 채팅 히스토리 로드
	loadChatHistory() {
			const savedHistory = Utils.session.get('chatHistory', []);
			if (savedHistory.length > 0) {
					this.state.messageHistory = savedHistory;
					// 필요시 UI에 이전 대화 복원
			}
	},
	
	// 채팅 히스토리 복원
	restoreChatHistory() {
			this.state.messageHistory.forEach(message => {
					if (message.type === 'user') {
							this.addUserMessage(message.content);
					} else if (message.type === 'bot') {
							this.addBotResponse(message.content);
					}
			});
			
			if (this.state.messageHistory.length > 0) {
					this.hideExampleQuestions();
			}
	},
	
	// 입력 제안 표시
	showInputSuggestions(input) {
			// 향후 구현: 입력에 따른 자동완성 제안
	},
	
	// 입력 제안 숨김
	hideInputSuggestions() {
			const suggestions = DOM.$('#inputSuggestions');
			if (suggestions) {
					DOM.hide(suggestions);
			}
	}
};