package io.factorialsystems.gatewayservice.filter;

import lombok.Getter;
import lombok.Setter;
import lombok.extern.slf4j.Slf4j;
import org.springframework.cloud.gateway.filter.GatewayFilter;
import org.springframework.cloud.gateway.filter.factory.AbstractGatewayFilterFactory;
import org.springframework.core.io.buffer.DataBuffer;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.server.reactive.ServerHttpRequest;
import org.springframework.http.server.reactive.ServerHttpResponse;
import org.springframework.security.oauth2.jwt.ReactiveJwtDecoder;
import org.springframework.stereotype.Component;
import reactor.core.publisher.Mono;

import java.nio.charset.StandardCharsets;

@Slf4j
@Component
public class JwtAuthFilterFactory extends AbstractGatewayFilterFactory<JwtAuthFilterFactory.Config> {

    private final ReactiveJwtDecoder jwtDecoder;

    public JwtAuthFilterFactory(ReactiveJwtDecoder jwtDecoder) {
        super(Config.class);
        this.jwtDecoder = jwtDecoder;
    }

    @Override
    public GatewayFilter apply(Config config) {
        return (exchange, chain) -> {
            ServerHttpRequest request = exchange.getRequest();
            String authHeader = request.getHeaders().getFirst(HttpHeaders.AUTHORIZATION);

            if (authHeader == null || !authHeader.startsWith("Bearer ")) {
                if (config.isRequired()) {
                    return onError(exchange.getResponse(), "Missing or invalid Authorization header");
                }
                return chain.filter(exchange);
            }

            String token = authHeader.substring(7);

            return jwtDecoder.decode(token)
                    .flatMap(jwt -> {
                        String userId = jwt.getSubject();
                        String orgId = jwt.getClaimAsString("org_id");
                        String role = jwt.getClaimAsString("role");

                        ServerHttpRequest mutatedRequest = request.mutate()
                                .header("X-User-ID", userId != null ? userId : "")
                                .header("X-Organization-ID", orgId != null ? orgId : "")
                                .header("X-User-Role", role != null ? role : "")
                                .build();

                        return chain.filter(exchange.mutate().request(mutatedRequest).build());
                    })
                    .onErrorResume(e -> {
                        log.warn("JWT validation failed: {}", e.getMessage());
                        if (config.isRequired()) {
                            return onError(exchange.getResponse(), "Invalid or expired token");
                        }
                        return chain.filter(exchange);
                    });
        };
    }

    private Mono<Void> onError(ServerHttpResponse response, String message) {
        response.setStatusCode(HttpStatus.UNAUTHORIZED);
        response.getHeaders().setContentType(MediaType.APPLICATION_JSON);
        String body = """
                {"error":{"code":"AUTH_003","message":"%s"}}""".formatted(message);
        DataBuffer buffer = response.bufferFactory().wrap(body.getBytes(StandardCharsets.UTF_8));
        return response.writeWith(Mono.just(buffer));
    }

    @Getter
    @Setter
    public static class Config {
        private boolean required = true;
    }
}
