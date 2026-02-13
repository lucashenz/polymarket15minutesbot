"""
Gerenciador automático de slugs para mercados de 5 minutos do BTC na Polymarket
Versão STANDALONE - Não requer pytz, usa apenas biblioteca padrão do Python
"""
from datetime import datetime, timedelta, timezone
from typing import Optional


class SlugManager:
    """Gerencia a geração automática de slugs para mercados BTC de 5 minutos"""
    
    def __init__(self, asset: str = "btc", interval_minutes: int = 5):
        """
        Inicializa o gerenciador de slugs
        
        Args:
            asset: Ativo a ser monitorado (padrão: "btc")
            interval_minutes: Intervalo em minutos (padrão: 5)
        """
        self.asset = asset.lower()
        self.interval_minutes = interval_minutes
        
        # Eastern Time é UTC-5 (EST) ou UTC-4 (EDT)
        # Vamos usar UTC-5 como padrão (ajuste se necessário para horário de verão)
        self.et_offset = timedelta(hours=-5)
        
        self._current_slug: Optional[str] = None
        self._current_period_start: Optional[datetime] = None
        self._current_period_end: Optional[datetime] = None
    
    def _get_current_et_time(self) -> datetime:
        """
        Retorna o horário atual em Eastern Time (UTC-5)
        
        NOTA: Esta implementação usa UTC-5 fixo (EST).
        Se quiser suporte automático a horário de verão (EDT = UTC-4),
        instale pytz e use a versão original do código.
        """
        utc_now = datetime.now(timezone.utc)
        et_now = utc_now + self.et_offset
        return et_now
    
    def _round_to_interval(self, dt: datetime) -> datetime:
        """
        Arredonda um datetime para o início do intervalo de 5 minutos
        
        Exemplos:
            10:52 -> 10:50
            10:57 -> 10:55
            11:03 -> 11:00
        """
        # Pega apenas minutos e arredonda para múltiplo de 5 para baixo
        minutes = (dt.minute // self.interval_minutes) * self.interval_minutes
        
        # Cria novo datetime com minutos arredondados e segundos/microssegundos zerados
        rounded = dt.replace(minute=minutes, second=0, microsecond=0)
        return rounded
    
    def _datetime_to_unix_timestamp(self, dt: datetime) -> int:
        """Converte datetime para Unix timestamp (segundos desde 1970)"""
        return int(dt.timestamp())
    
    def _generate_slug(self, period_start: datetime) -> str:
        """
        Gera o slug baseado no horário de início do período
        
        Formato: {asset}-updown-{interval}m-{unix_timestamp}
        Exemplo: btc-updown-5m-1770998100
        """
        unix_time = self._datetime_to_unix_timestamp(period_start)
        slug = f"{self.asset}-updown-{self.interval_minutes}m-{unix_time}"
        return slug
    
    def get_current_slug(self) -> str:
        """
        Retorna o slug para o período atual de 5 minutos
        Atualiza automaticamente se estamos em um novo período
        
        Returns:
            str: Slug atual (ex: "btc-updown-5m-1770998100")
        """
        now = self._get_current_et_time()
        period_start = self._round_to_interval(now)
        period_end = period_start + timedelta(minutes=self.interval_minutes)
        
        # Verifica se mudou de período
        if self._current_period_start != period_start:
            self._current_period_start = period_start
            self._current_period_end = period_end
            self._current_slug = self._generate_slug(period_start)
            
            print(f"[SlugManager] Novo período detectado!")
            print(f"  Período: {period_start.strftime('%H:%M')} - {period_end.strftime('%H:%M')} ET")
            print(f"  Slug: {self._current_slug}")
        
        return self._current_slug
    
    def get_next_slug(self) -> str:
        """
        Retorna o slug para o PRÓXIMO período de 5 minutos
        Útil para preparar o sistema antes da mudança
        
        Returns:
            str: Slug do próximo período
        """
        now = self._get_current_et_time()
        current_period_start = self._round_to_interval(now)
        next_period_start = current_period_start + timedelta(minutes=self.interval_minutes)
        
        return self._generate_slug(next_period_start)
    
    def get_time_until_next_period(self) -> int:
        """
        Retorna quantos segundos faltam até o próximo período
        
        Returns:
            int: Segundos até a próxima atualização
        """
        now = self._get_current_et_time()
        current_period_start = self._round_to_interval(now)
        next_period_start = current_period_start + timedelta(minutes=self.interval_minutes)
        
        delta = next_period_start - now
        return int(delta.total_seconds())
    
    def get_period_info(self) -> dict:
        """
        Retorna informações completas sobre o período atual
        
        Returns:
            dict com:
                - slug: slug atual
                - period_start: início do período (datetime)
                - period_end: fim do período (datetime)
                - time_remaining: segundos até o próximo período
                - next_slug: slug do próximo período
        """
        current_slug = self.get_current_slug()
        next_slug = self.get_next_slug()
        time_remaining = self.get_time_until_next_period()
        
        return {
            'slug': current_slug,
            'period_start': self._current_period_start,
            'period_end': self._current_period_end,
            'time_remaining': time_remaining,
            'next_slug': next_slug,
            'asset': self.asset,
            'interval_minutes': self.interval_minutes
        }
    
    def should_update(self) -> bool:
        """
        Verifica se é hora de atualizar para um novo período
        
        Returns:
            bool: True se mudou de período desde a última verificação
        """
        old_slug = self._current_slug
        new_slug = self.get_current_slug()
        return old_slug != new_slug


# Exemplo de uso
if __name__ == "__main__":
    import time
    
    manager = SlugManager(asset="btc", interval_minutes=5)
    
    print("=== TESTE DO SLUG MANAGER ===\n")
    
    # Mostra informações do período atual
    info = manager.get_period_info()
    print(f"Slug Atual: {info['slug']}")
    print(f"Período: {info['period_start'].strftime('%H:%M')} - {info['period_end'].strftime('%H:%M')} ET")
    print(f"Tempo restante: {info['time_remaining']} segundos ({info['time_remaining']//60} minutos)")
    print(f"Próximo slug: {info['next_slug']}\n")
    
    # Simula verificação contínua (você rodaria isso no seu loop principal)
    print("Simulando monitoramento contínuo (Ctrl+C para parar)...\n")
    try:
        while True:
            # Verifica se mudou de período
            if manager.should_update():
                info = manager.get_period_info()
                print(f"\n🔄 SLUG ATUALIZADO!")
                print(f"  Novo slug: {info['slug']}")
                print(f"  Período: {info['period_start'].strftime('%H:%M')} - {info['period_end'].strftime('%H:%M')} ET\n")
            
            # Em produção, você checaria isso a cada 10-30 segundos
            time.sleep(10)
            
    except KeyboardInterrupt:
        print("\n\nMonitoramento interrompido.")