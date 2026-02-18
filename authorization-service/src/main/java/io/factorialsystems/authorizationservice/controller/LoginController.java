package io.factorialsystems.authorizationservice.controller;

import io.factorialsystems.authorizationservice.dto.request.RegisterRequest;
import io.factorialsystems.authorizationservice.service.AuthService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.validation.BindingResult;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.ModelAttribute;
import org.springframework.web.bind.annotation.PostMapping;

@Slf4j
@Controller
@RequiredArgsConstructor
public class LoginController {

    private final AuthService authService;

    @GetMapping("/login")
    public String login() {
        return "login";
    }

    @GetMapping("/register")
    public String showRegisterForm(Model model) {
        model.addAttribute("registerRequest", new RegisterRequest());
        return "register";
    }

    @PostMapping("/register")
    public String register(@Valid @ModelAttribute("registerRequest") RegisterRequest request,
                           BindingResult bindingResult,
                           Model model) {
        if (bindingResult.hasErrors()) {
            String errorMessage = bindingResult.getFieldErrors().stream()
                    .map(e -> e.getDefaultMessage())
                    .findFirst()
                    .orElse("Please fix the errors below.");
            model.addAttribute("error", errorMessage);
            return "register";
        }

        try {
            authService.register(request);
            return "redirect:/login?registered";
        } catch (Exception e) {
            log.warn("Registration failed: {}", e.getMessage());
            model.addAttribute("error", e.getMessage());
            return "register";
        }
    }
}
